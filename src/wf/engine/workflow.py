"""Deterministic interpreter workflow (FR-10, PLAN §5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from wf.definition.models import Definition, Step, parse_duration
    from wf.engine import activities
    from wf.schemas.core import HumanDecision

AGENT_RETRY = RetryPolicy(maximum_attempts=3)
SHORT_RETRY = RetryPolicy(maximum_attempts=3)
AGENT_TIMEOUT = timedelta(minutes=5)
SHORT_TIMEOUT = timedelta(seconds=30)
MAIL_TIMEOUT = timedelta(seconds=60)


@dataclass
class WorkflowInput:
    """Input to InterpreterWorkflow."""

    definition_json: dict[str, Any]
    inputs: dict[str, Any]
    initiator: str
    run_id: str
    auto_approve: bool = False


@dataclass
class StatusView:
    """Queryable run status (FR-18)."""

    run_id: str
    workflow_id: str
    current_step: str
    status: str
    pending_human: bool
    attempt: int
    nonce: str | None
    data: dict[str, Any] | None
    eval: dict[str, Any] | None
    checks: list[dict[str, Any]]
    reviewers: list[str]
    schema_name: str


@dataclass
class PendingGate:
    """In-memory HITL gate."""

    step_id: str
    attempt: int
    nonce: str
    data: dict[str, Any]
    eval: dict[str, Any]
    checks: list[dict[str, Any]]
    schema_name: str
    timeout: timedelta


@workflow.defn
class InterpreterWorkflow:
    """Single interpreter type. Definition is passed in as input (D1, D2)."""

    def __init__(self) -> None:
        self._decision: HumanDecision | None = None
        self._status = "running"
        self._current_step = ""
        self._pending: PendingGate | None = None
        self._reviewers: list[str] = []
        self._workflow_id = ""
        self._run_id = ""

    @workflow.signal
    def human_decision(self, decision: HumanDecision) -> None:
        """Accept a reviewer decision if it matches the pending gate."""
        self._decision = decision

    @workflow.query
    def status(self) -> dict[str, Any]:
        """Return the current step and any pending human payload."""
        pending = self._pending
        return {
            "run_id": self._run_id,
            "workflow_id": self._workflow_id,
            "current_step": self._current_step,
            "status": self._status,
            "pending_human": pending is not None,
            "attempt": pending.attempt if pending else 0,
            "nonce": pending.nonce if pending else None,
            "data": pending.data if pending else None,
            "eval": pending.eval if pending else None,
            "checks": pending.checks if pending else [],
            "reviewers": self._reviewers,
            "schema_name": pending.schema_name if pending else "",
        }

    @workflow.run
    async def run(self, payload: WorkflowInput) -> dict[str, Any]:
        """Interpret the definition sequentially."""
        definition = Definition.model_validate(payload.definition_json)
        self._run_id = payload.run_id
        self._workflow_id = definition.workflow.id
        self._reviewers = list(definition.workflow.reviewers)
        ctx: dict[str, Any] = {}
        steps: dict[str, Any] = {}
        run_status = "completed"

        for step in definition.steps:
            self._current_step = step.id
            envelope = await self._run_step(definition, step, payload, ctx, steps)
            steps[step.id] = envelope
            status = envelope["system"]["status"]
            if status in {"stopped", "failed"}:
                run_status = status
                break

        if run_status == "completed":
            await self._deliver(definition, payload, steps)

        self._status = run_status
        self._pending = None
        return {"run_id": payload.run_id, "status": run_status, "steps": list(steps)}

    async def _run_step(
        self,
        definition: Definition,
        step: Step,
        payload: WorkflowInput,
        ctx: dict[str, Any],
        steps: dict[str, Any],
    ) -> dict[str, Any]:
        base_ctx = {"inputs": payload.inputs, "ctx": ctx, "steps": steps}
        if step.run_when:
            should_run = await workflow.execute_activity(
                activities.evaluate_expression,
                args=[step.run_when, base_ctx],
                start_to_close_timeout=SHORT_TIMEOUT,
                retry_policy=SHORT_RETRY,
            )
            if not should_run:
                return await self._persist_skip(definition, step, payload)

        attempt = 1
        human_feedback: str | None = None
        while True:
            await self._resolve_prereqs(definition, step, payload, ctx, steps, attempt)
            step_input = await workflow.execute_activity(
                activities.map_step_input,
                args=[step.input, {"inputs": payload.inputs, "ctx": ctx, "steps": steps}],
                start_to_close_timeout=SHORT_TIMEOUT,
                retry_policy=SHORT_RETRY,
            )
            data, checks, eval_meta, usage, models = await self._loop_agents(
                definition, step, payload, ctx, steps, step_input, human_feedback, attempt
            )
            action = await self._maybe_hitl(definition, step, payload, data, eval_meta, checks, attempt)
            if action == "redo":
                attempt += 1
                human_feedback = (self._decision.feedback if self._decision else "") or ""
                self._decision = None
                self._pending = None
                continue
            if action == "stop":
                return await self._persist_terminal(
                    definition,
                    step,
                    payload,
                    status="stopped",
                    attempt=attempt,
                    data=data,
                    eval_meta=eval_meta,
                    checks=checks,
                    usage=usage,
                    models=models,
                    human=self._human_info(action, payload),
                )
            human: dict[str, Any] | None
            if action == "proceed_modified" and self._decision and self._decision.modified_data:
                data = await workflow.execute_activity(
                    activities.validate_modified_data_activity,
                    args=[
                        {
                            "schema_name": step.executor.output_schema if step.executor else "",
                            "data": self._decision.modified_data,
                        }
                    ],
                    start_to_close_timeout=SHORT_TIMEOUT,
                    retry_policy=SHORT_RETRY,
                )
                warning_ctx = {"inputs": payload.inputs, "ctx": ctx, "steps": steps, "data": data}
                warnings = await workflow.execute_activity(
                    activities.run_checks_activity,
                    args=[
                        {
                            "data": data,
                            "context": warning_ctx,
                            "tool_trace": [],
                            "cel_checks": step.evaluator.checks if step.evaluator else [],
                            "named_checks": step.evaluator.named_checks if step.evaluator else [],
                        }
                    ],
                    start_to_close_timeout=SHORT_TIMEOUT,
                    retry_policy=SHORT_RETRY,
                )
                modified_human = self._human_info(action, payload) or {}
                modified_human["check_warnings"] = warnings
                modified_human["modified"] = True
                modified_human["diff"] = {"changed": True}
                human = modified_human
            else:
                human = self._human_info(action, payload) if action else None
            return await self._persist_terminal(
                definition,
                step,
                payload,
                status="completed",
                attempt=attempt,
                data=data,
                eval_meta=eval_meta,
                checks=checks,
                usage=usage,
                models=models,
                human=human,
            )

    async def _resolve_prereqs(
        self,
        definition: Definition,
        step: Step,
        payload: WorkflowInput,
        ctx: dict[str, Any],
        steps: dict[str, Any],
        attempt: int,
    ) -> None:
        max_iter = definition.workflow.defaults.max_iterations
        model_id = definition.workflow.defaults.model or ""
        for prereq in step.prerequisites:
            check_ctx = {"inputs": payload.inputs, "ctx": ctx, "steps": steps, "data": {}}
            ok = await workflow.execute_activity(
                activities.evaluate_expression,
                args=[prereq.check, check_ctx],
                start_to_close_timeout=SHORT_TIMEOUT,
                retry_policy=SHORT_RETRY,
            )
            if ok:
                continue
            last_error = "prerequisite unresolved"
            for _ in range(max_iter):
                resolved = await workflow.execute_activity(
                    activities.run_resolver_activity,
                    args=[
                        {
                            "run_id": payload.run_id,
                            "step_id": step.id,
                            "attempt": attempt,
                            "model_id": model_id,
                            "instructions": prereq.resolve.instructions,
                            "output_schema": prereq.resolve.output_schema,
                            "tools": prereq.resolve.tools,
                            "inputs": payload.inputs,
                        }
                    ],
                    start_to_close_timeout=AGENT_TIMEOUT,
                    retry_policy=AGENT_RETRY,
                )
                data = resolved["data"]
                verify_ctx = {"inputs": payload.inputs, "ctx": ctx, "steps": steps, "data": data}
                verified = True
                for expr in prereq.resolve.verify:
                    passed = await workflow.execute_activity(
                        activities.evaluate_expression,
                        args=[expr, verify_ctx],
                        start_to_close_timeout=SHORT_TIMEOUT,
                        retry_policy=SHORT_RETRY,
                    )
                    if not passed:
                        verified = False
                        last_error = f"verify failed: {expr}"
                        break
                if verified:
                    _bind(ctx, prereq.bind, data)
                    break
            else:
                await workflow.execute_activity(
                    activities.send_notification_activity,
                    args=[
                        {
                            "to": payload.initiator,
                            "template": "failed.html",
                            "subject": f"Workflow {definition.workflow.id} failed",
                            "context": {
                                "run_id": payload.run_id,
                                "step_id": step.id,
                                "reason": last_error,
                            },
                        }
                    ],
                    start_to_close_timeout=MAIL_TIMEOUT,
                    retry_policy=SHORT_RETRY,
                )
                raise ApplicationError(last_error, non_retryable=True)

    async def _loop_agents(
        self,
        definition: Definition,
        step: Step,
        payload: WorkflowInput,
        ctx: dict[str, Any],
        steps: dict[str, Any],
        step_input: dict[str, Any],
        human_feedback: str | None,
        attempt: int,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, int], dict[str, str]]:
        assert step.executor is not None
        defaults = definition.workflow.defaults
        exec_model = defaults.model or ""
        eval_model = defaults.evaluator_model or exec_model
        previous = None
        failed_checks: list[dict[str, Any]] | None = None
        feedback: str | None = None
        usage = {"input_tokens": 0, "output_tokens": 0}
        data: dict[str, Any] = {}
        checks: list[dict[str, Any]] = []
        eval_meta: dict[str, Any] = {"verdict": "fail", "score": 0.0, "iterations": 0, "unmet_criteria": []}
        for iteration in range(1, defaults.max_iterations + 1):
            executed = await workflow.execute_activity(
                activities.run_executor_activity,
                args=[
                    {
                        "run_id": payload.run_id,
                        "step_id": step.id,
                        "attempt": attempt,
                        "model_id": exec_model,
                        "instructions": step.executor.instructions,
                        "output_schema": step.executor.output_schema,
                        "tools": step.executor.tools,
                        "step_input": step_input,
                        "previous_output": previous,
                        "failed_checks": failed_checks,
                        "evaluator_feedback": feedback,
                        "human_feedback": human_feedback,
                    }
                ],
                start_to_close_timeout=AGENT_TIMEOUT,
                retry_policy=AGENT_RETRY,
            )
            data = executed["data"]
            usage = _add_usage(usage, executed.get("usage") or {})
            check_ctx = {"inputs": payload.inputs, "ctx": ctx, "steps": steps, "data": data}
            checks = await workflow.execute_activity(
                activities.run_checks_activity,
                args=[
                    {
                        "data": data,
                        "context": check_ctx,
                        "tool_trace": executed.get("trace") or [],
                        "cel_checks": step.evaluator.checks if step.evaluator else [],
                        "named_checks": step.evaluator.named_checks if step.evaluator else [],
                    }
                ],
                start_to_close_timeout=SHORT_TIMEOUT,
                retry_policy=SHORT_RETRY,
            )
            judged = await workflow.execute_activity(
                activities.run_evaluator_activity,
                args=[
                    {
                        "run_id": payload.run_id,
                        "step_id": step.id,
                        "attempt": attempt,
                        "model_id": eval_model,
                        "objective": step.executor.instructions,
                        "rubric": step.evaluator.rubric if step.evaluator else [],
                        "candidate": data,
                        "check_results": checks,
                    }
                ],
                start_to_close_timeout=AGENT_TIMEOUT,
                retry_policy=AGENT_RETRY,
            )
            usage = _add_usage(usage, judged.get("usage") or {})
            verdict = judged["verdict"]
            eval_meta = {
                "verdict": verdict["verdict"],
                "score": verdict.get("score") or 0.0,
                "iterations": iteration,
                "unmet_criteria": verdict.get("unmet_criteria") or [],
                "checks": checks,
            }
            if verdict["verdict"] == "pass":
                return data, checks, eval_meta, usage, {"executor": exec_model, "evaluator": eval_model}
            previous = data
            failed_checks = [c for c in checks if not c.get("passed")]
            feedback = verdict.get("feedback") or ""
        if defaults.on_exhausted == "fail":
            await workflow.execute_activity(
                activities.send_notification_activity,
                args=[
                    {
                        "to": payload.initiator,
                        "template": "failed.html",
                        "subject": f"Workflow {definition.workflow.id} failed",
                        "context": {"run_id": payload.run_id, "step_id": step.id, "reason": "exhausted"},
                    }
                ],
                start_to_close_timeout=MAIL_TIMEOUT,
                retry_policy=SHORT_RETRY,
            )
            raise ApplicationError("evaluator loop exhausted", non_retryable=True)
        eval_meta["verdict"] = "escalated"
        return data, checks, eval_meta, usage, {"executor": exec_model, "evaluator": eval_model}

    async def _maybe_hitl(
        self,
        definition: Definition,
        step: Step,
        payload: WorkflowInput,
        data: dict[str, Any],
        eval_meta: dict[str, Any],
        checks: list[dict[str, Any]],
        attempt: int,
    ) -> str | None:
        required = False
        if step.human_review:
            required = bool(
                await workflow.execute_activity(
                    activities.evaluate_expression,
                    args=[
                        step.human_review.required_when,
                        {
                            "inputs": payload.inputs,
                            "ctx": {},
                            "steps": {},
                            "system": {"eval": eval_meta},
                        },
                    ],
                    start_to_close_timeout=SHORT_TIMEOUT,
                    retry_policy=SHORT_RETRY,
                )
            )
        escalated = eval_meta.get("verdict") == "escalated"
        if not required and not escalated:
            return None
        if payload.auto_approve:
            self._decision = HumanDecision(
                action="proceed",
                reviewer="auto",
                attempt=attempt,
                nonce="auto",
                feedback="auto-approve",
            )
            return "proceed"
        nonce = str(workflow.uuid4())
        timeout = parse_duration(definition.workflow.defaults.hitl.timeout)
        self._pending = PendingGate(
            step_id=step.id,
            attempt=attempt,
            nonce=nonce,
            data=data,
            eval=eval_meta,
            checks=checks,
            schema_name=step.executor.output_schema if step.executor else "",
            timeout=timeout,
        )
        await workflow.execute_activity(
            activities.send_review_email_activity,
            args=[
                {
                    "run_id": payload.run_id,
                    "workflow_id": definition.workflow.id,
                    "step_id": step.id,
                    "attempt": attempt,
                    "nonce": nonce,
                    "reviewers": definition.workflow.reviewers,
                    "verdict": eval_meta,
                    "timeout_seconds": int(timeout.total_seconds()),
                }
            ],
            start_to_close_timeout=MAIL_TIMEOUT,
            retry_policy=SHORT_RETRY,
        )
        self._decision = None
        try:
            await workflow.wait_condition(
                lambda: self._accepted_decision() is not None,
                timeout=timeout,
            )
        except TimeoutError:
            await workflow.execute_activity(
                activities.send_notification_activity,
                args=[
                    {
                        "to": payload.initiator,
                        "template": "stopped.html",
                        "subject": f"Workflow {definition.workflow.id} stopped",
                        "context": {
                            "run_id": payload.run_id,
                            "step_id": step.id,
                            "who": "timeout",
                        },
                    }
                ],
                start_to_close_timeout=MAIL_TIMEOUT,
                retry_policy=SHORT_RETRY,
            )
            return "stop"
        decision = self._accepted_decision()
        assert decision is not None
        self._decision = decision
        if decision.action == "stop":
            await workflow.execute_activity(
                activities.send_notification_activity,
                args=[
                    {
                        "to": payload.initiator,
                        "template": "stopped.html",
                        "subject": f"Workflow {definition.workflow.id} stopped",
                        "context": {
                            "run_id": payload.run_id,
                            "step_id": step.id,
                            "who": decision.reviewer,
                        },
                    }
                ],
                start_to_close_timeout=MAIL_TIMEOUT,
                retry_policy=SHORT_RETRY,
            )
        return decision.action

    def _accepted_decision(self) -> HumanDecision | None:
        pending = self._pending
        decision = self._decision
        if pending is None or decision is None:
            return None
        if decision.attempt != pending.attempt or decision.nonce != pending.nonce:
            return None
        return decision

    def _human_info(self, action: str | None, payload: WorkflowInput) -> dict[str, Any] | None:
        if action is None or self._decision is None:
            return None
        return {
            "required": True,
            "decision": action,
            "reviewer": self._decision.reviewer,
            "decided_at": workflow.now().isoformat(),
            "feedback": self._decision.feedback or "",
            "modified": action == "proceed_modified",
            "check_warnings": [],
            "diff": None,
        }

    async def _persist_skip(self, definition: Definition, step: Step, payload: WorkflowInput) -> dict[str, Any]:
        envelope = {
            "system": {
                "run_id": payload.run_id,
                "workflow_id": definition.workflow.id,
                "definition_version": definition.workflow.version,
                "step_id": step.id,
                "step_type": step.type,
                "schema": step.executor.output_schema if step.executor else "",
                "status": "skipped",
                "attempt": 1,
                "eval": {"verdict": None, "score": 0, "iterations": 0, "unmet_criteria": [], "checks": []},
                "human": {
                    "required": False,
                    "decision": None,
                    "reviewer": "",
                    "decided_at": None,
                    "feedback": "",
                    "modified": False,
                    "check_warnings": [],
                    "diff": None,
                },
                "model": {"executor": "", "evaluator": ""},
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "artifact_uri": "",
                "started_at": workflow.now().isoformat(),
                "completed_at": workflow.now().isoformat(),
            },
            "data": {},
        }
        uri = await workflow.execute_activity(
            activities.persist_envelope_activity,
            args=[{"envelope": envelope}],
            start_to_close_timeout=SHORT_TIMEOUT,
            retry_policy=SHORT_RETRY,
        )
        envelope["system"]["artifact_uri"] = uri
        return envelope

    async def _persist_terminal(
        self,
        definition: Definition,
        step: Step,
        payload: WorkflowInput,
        *,
        status: str,
        attempt: int,
        data: dict[str, Any],
        eval_meta: dict[str, Any],
        checks: list[dict[str, Any]],
        usage: dict[str, int],
        models: dict[str, str],
        human: dict[str, Any] | None,
    ) -> dict[str, Any]:
        envelope = {
            "system": {
                "run_id": payload.run_id,
                "workflow_id": definition.workflow.id,
                "definition_version": definition.workflow.version,
                "step_id": step.id,
                "step_type": step.type,
                "schema": step.executor.output_schema if step.executor else "",
                "status": status,
                "attempt": attempt,
                "eval": eval_meta,
                "human": human
                or {
                    "required": False,
                    "decision": None,
                    "reviewer": "",
                    "decided_at": None,
                    "feedback": "",
                    "modified": False,
                    "check_warnings": [],
                    "diff": None,
                },
                "model": models,
                "usage": usage,
                "artifact_uri": "",
                "started_at": workflow.now().isoformat(),
                "completed_at": workflow.now().isoformat(),
            },
            "data": data,
        }
        uri = await workflow.execute_activity(
            activities.persist_envelope_activity,
            args=[{"envelope": envelope}],
            start_to_close_timeout=SHORT_TIMEOUT,
            retry_policy=SHORT_RETRY,
        )
        envelope["system"]["artifact_uri"] = uri
        self._pending = None
        return envelope

    async def _deliver(self, definition: Definition, payload: WorkflowInput, steps: dict[str, Any]) -> None:
        from_step = definition.output.from_step
        plan = (steps.get(from_step) or {}).get("data") or {}
        forecast = (steps.get("get_forecast") or {}).get("data") or {}
        advisory_env = steps.get("safety_advisory") or {}
        advisory = advisory_env.get("data") if (advisory_env.get("system") or {}).get("status") == "completed" else None
        create = steps.get("create_plan") or {}
        await workflow.execute_activity(
            activities.render_and_deliver_activity,
            args=[
                {
                    "run_id": payload.run_id,
                    "workflow_id": definition.workflow.id,
                    "initiator": payload.initiator,
                    "subject": definition.output.deliver.subject,
                    "attach": definition.output.deliver.attach,
                    "expression_context": {
                        "inputs": payload.inputs,
                        "ctx": {},
                        "steps": steps,
                    },
                    "context": {
                        "forecast": forecast,
                        "advisory": advisory,
                        "plan": plan,
                        "run_id": payload.run_id,
                        "approval": (create.get("system") or {}).get("human") or {},
                    },
                }
            ],
            start_to_close_timeout=MAIL_TIMEOUT,
            retry_policy=SHORT_RETRY,
        )


def _bind(ctx: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    if not parts or parts[0] != "ctx":
        ctx[path] = value
        return
    target = ctx
    for part in parts[1:-1]:
        nxt = target.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            target[part] = nxt
        target = nxt
    if parts[1:]:
        target[parts[-1]] = value


def _add_usage(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    return {
        "input_tokens": int(left.get("input_tokens") or 0) + int(right.get("input_tokens") or 0),
        "output_tokens": int(left.get("output_tokens") or 0) + int(right.get("output_tokens") or 0),
    }
