"""Temporal activities: agents, checks, persist, email, render."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from wf.agents.evaluator import run_evaluator
from wf.agents.executor import run_executor
from wf.agents.resolver import run_resolver
from wf.checks.registry import run_named_check
from wf.config import get_settings
from wf.errors import ExpressionError, ToolError
from wf.expressions.cel import evaluate_cel
from wf.expressions.template import interpolate
from wf.logging import bind_run, get_logger
from wf.notify.email import send_html_email
from wf.render.pdf import render_weather_plan_pdf
from wf.schemas.core import CheckResult, Envelope, SystemMeta
from wf.schemas.registry import get_schema
from wf.storage.artifacts import get_artifact_store


def _nonretryable(message: str) -> ApplicationError:
    return ApplicationError(message, non_retryable=True)


@activity.defn
async def evaluate_expression(source: str, context: dict[str, Any]) -> Any:
    """Evaluate a CEL expression in an activity (sandbox-safe)."""
    try:
        return evaluate_cel(source, context)
    except ExpressionError as exc:
        raise _nonretryable(str(exc)) from exc


@activity.defn
async def map_step_input(mapping: dict[str, str], context: dict[str, Any]) -> dict[str, Any]:
    """Evaluate each `input:` CEL mapping."""
    result: dict[str, Any] = {}
    for key, expr in mapping.items():
        try:
            result[key] = evaluate_cel(expr, context)
        except ExpressionError as exc:
            raise _nonretryable(f"input.{key}: {exc}") from exc
    return result


@activity.defn
async def run_resolver_activity(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the prerequisite resolver agent."""
    bind_run(run_id=payload["run_id"], step_id=payload.get("step_id", ""), attempt=payload.get("attempt", 1))
    try:
        data, trace, usage = await run_resolver(
            model_id=payload["model_id"],
            instructions=payload["instructions"],
            output_schema=payload["output_schema"],
            tools=payload.get("tools") or [],
            inputs=payload.get("inputs") or {},
            run_id=payload.get("run_id"),
        )
    except ToolError as exc:
        raise _nonretryable(str(exc)) from exc
    return {"data": data, "trace": trace, "usage": usage}


@activity.defn
async def run_executor_activity(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the executor agent."""
    bind_run(run_id=payload["run_id"], step_id=payload.get("step_id", ""), attempt=payload.get("attempt", 1))
    data, trace, usage = await run_executor(
        model_id=payload["model_id"],
        instructions=payload["instructions"],
        output_schema=payload["output_schema"],
        tools=payload.get("tools") or [],
        step_input=payload.get("step_input") or {},
        previous_output=payload.get("previous_output"),
        failed_checks=payload.get("failed_checks"),
        evaluator_feedback=payload.get("evaluator_feedback"),
        human_feedback=payload.get("human_feedback"),
    )
    return {"data": data, "trace": trace, "usage": usage}


@activity.defn
async def run_action_activity(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Run a deterministic action step (direct tool call, no LLM).
    
    This bypasses the executor/evaluator loop and calls the tool directly.
    """
    import time
    from wf.tools.truecare import TRUECARE_TOOLS
    from wf.tools.openmeteo import geocode_location, get_daily_forecast
    
    bind_run(
        run_id=payload["run_id"],
        step_id=payload.get("step_id", ""),
        attempt=payload.get("attempt", 1),
    )
    
    tool_name = payload["tool_name"]
    tool_input = payload.get("tool_input") or {}
    output_schema = payload.get("output_schema", "ActionResult@1")
    on_error = payload.get("on_error", "fail")
    
    # Tool registry - combine all available tools
    all_tools = {
        **TRUECARE_TOOLS,
        "geocode_location": geocode_location,
        "get_daily_forecast": get_daily_forecast,
    }
    
    tool_fn = all_tools.get(tool_name)
    if tool_fn is None:
        error_msg = f"Unknown action tool: {tool_name}"
        if on_error == "fail":
            raise _nonretryable(error_msg)
        return {
            "data": {"success": False, "error": error_msg, "tool_name": tool_name, "data": {}},
            "trace": [],
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
    
    start_time = time.time()
    try:
        # Call the tool directly
        if hasattr(tool_fn, "__call__"):
            import inspect
            if inspect.iscoroutinefunction(tool_fn):
                # Async tool - check if it takes a Pydantic model or kwargs
                sig = inspect.signature(tool_fn)
                params = list(sig.parameters.keys())
                if len(params) == 1 and not params[0].startswith("*"):
                    # Likely takes a single Pydantic model input
                    # Try to find the input class
                    from wf.tools import truecare
                    input_class_name = tool_name.replace("_", " ").title().replace(" ", "") + "Input"
                    input_class = getattr(truecare, input_class_name, None)
                    if input_class:
                        input_obj = input_class(**tool_input)
                        result = await tool_fn(input_obj)
                    else:
                        result = await tool_fn(**tool_input)
                else:
                    result = await tool_fn(**tool_input)
            else:
                result = tool_fn(**tool_input)
        else:
            raise _nonretryable(f"Tool {tool_name} is not callable")
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Convert result to dict if it's a Pydantic model
        if hasattr(result, "model_dump"):
            result_data = result.model_dump()
        elif isinstance(result, dict):
            result_data = result
        else:
            result_data = {"result": result}
        
        # Wrap in ActionResult format
        data = {
            "success": not result_data.get("error", False),
            "data": result_data,
            "error": result_data.get("reason") if result_data.get("error") else None,
            "tool_name": tool_name,
            "duration_ms": duration_ms,
        }
        
        return {
            "data": data,
            "trace": [{"tool": tool_name, "input": tool_input, "output": result_data}],
            "usage": {"input_tokens": 0, "output_tokens": 0},  # No LLM usage
        }
        
    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(exc)
        
        if on_error == "fail":
            raise _nonretryable(error_msg) from exc
        
        return {
            "data": {
                "success": False,
                "data": {},
                "error": error_msg,
                "tool_name": tool_name,
                "duration_ms": duration_ms,
            },
            "trace": [{"tool": tool_name, "input": tool_input, "error": error_msg}],
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }


@activity.defn
async def run_checks_activity(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Run CEL then named checks. Pydantic validation is implied by typed executor output."""
    data = payload["data"]
    context = payload["context"]
    tool_trace = payload.get("tool_trace") or []
    results: list[dict[str, Any]] = []
    for expr in payload.get("cel_checks") or []:
        try:
            passed = bool(evaluate_cel(expr, {**context, "data": data}))
            results.append(CheckResult(name=expr, passed=passed).model_dump())
        except ExpressionError as exc:
            results.append(CheckResult(name=expr, passed=False, detail=str(exc)).model_dump())
    for name in payload.get("named_checks") or []:
        result = run_named_check(name, data, context, tool_trace)
        results.append(result.model_dump())
    return results


@activity.defn
async def run_evaluator_activity(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the evaluator agent and enforce the check gate."""
    bind_run(run_id=payload["run_id"], step_id=payload.get("step_id", ""), attempt=payload.get("attempt", 1))
    verdict, usage = await run_evaluator(
        model_id=payload["model_id"],
        objective=payload.get("objective") or "",
        rubric=payload.get("rubric") or [],
        candidate=payload["candidate"],
        check_results=payload.get("check_results") or [],
    )
    return {"verdict": verdict.model_dump(), "usage": usage}


@activity.defn
async def persist_envelope_activity(payload: dict[str, Any]) -> str:
    """Persist a terminal envelope to the artifact store."""
    envelope = Envelope.model_validate(payload["envelope"])
    store = get_artifact_store()
    key = f"runs/{envelope.system.run_id}/steps/{envelope.system.step_id}.json"
    uri = store.put_text(key, envelope.model_dump_json())
    get_logger().info("envelope_persisted", artifact_uri=uri)
    return uri


@activity.defn
async def send_review_email_activity(payload: dict[str, Any]) -> None:
    """Email reviewers a review link."""
    settings = get_settings()
    from wf.hitl.tokens import sign_review_token

    token = sign_review_token(
        run_id=payload["run_id"],
        step_id=payload["step_id"],
        attempt=payload["attempt"],
        nonce=payload["nonce"],
        max_age=payload.get("timeout_seconds") or 259200,
    )
    link = f"{settings.wf_review_base_url.rstrip('/')}/review/{token}"
    body = _render_email(
        "review.html",
        {
            "workflow_id": payload.get("workflow_id", ""),
            "step_id": payload["step_id"],
            "attempt": payload["attempt"],
            "verdict": payload.get("verdict", {}),
            "link": link,
        },
    )
    send_html_email(
        to_addresses=payload["reviewers"],
        subject=f"Review {payload.get('workflow_id')} / {payload['step_id']}",
        html=body,
    )


@activity.defn
async def send_notification_activity(payload: dict[str, Any]) -> None:
    """Email the initiator about stop/fail/delivery."""
    template = payload.get("template") or "failed.html"
    body = _render_email(template, payload.get("context") or {})
    send_html_email(
        to_addresses=[payload["to"]],
        subject=payload.get("subject") or "Workflow update",
        html=body,
        attachments=payload.get("attachments") or [],
    )


@activity.defn
async def render_and_deliver_activity(payload: dict[str, Any]) -> dict[str, Any]:
    """Render PDF, store it, and email the initiator."""
    settings = get_settings()
    store = get_artifact_store()
    pdf = render_weather_plan_pdf(payload["context"])
    key = f"runs/{payload['run_id']}/output/{payload['workflow_id']}.pdf"
    uri = store.put_bytes(key, pdf, "application/pdf")
    link = store.presign(key, settings.wf_presign_expiry_seconds)
    subject = interpolate(payload["subject"], payload.get("expression_context") or {})
    if payload.get("attach", True):
        send_html_email(
            to_addresses=[payload["initiator"]],
            subject=subject,
            html=_render_email("delivered.html", {"link": link, "run_id": payload["run_id"]}),
            attachments=[{"filename": f"{payload['workflow_id']}.pdf", "content": pdf}],
        )
    return {"artifact_uri": uri, "link": link}


@activity.defn
async def validate_modified_data_activity(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate proceed_modified JSON against the step schema."""
    schema = get_schema(payload["schema_name"])
    if schema is None:
        raise _nonretryable(f"unknown schema {payload['schema_name']}")
    try:
        model = schema.model_validate(payload["data"])
    except Exception as exc:  # noqa: BLE001
        raise _nonretryable(f"invalid modified data: {exc}") from exc
    return model.model_dump(mode="json")


def utcnow() -> datetime:
    """Return timezone-aware UTC now (activity-side only)."""
    return datetime.now(UTC)


def _render_email(name: str, context: dict[str, Any]) -> str:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    from wf.notify.email import email_template_dir

    env = Environment(
        loader=FileSystemLoader(str(email_template_dir())),
        autoescape=select_autoescape(["html"]),
    )
    return env.get_template(name).render(**context)


def json_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow JSON diff for FR-58."""
    return {"before": before, "after": after, "changed": before != after}


def envelope_dump(envelope: Envelope) -> dict[str, Any]:
    """Serialize an envelope to a workflow-safe dict."""
    loaded: dict[str, Any] = json.loads(envelope.model_dump_json())
    return loaded


def new_system(**kwargs: Any) -> dict[str, Any]:
    """Build a SystemMeta dict."""
    meta = SystemMeta(**kwargs)
    loaded: dict[str, Any] = json.loads(meta.model_dump_json(by_alias=True))
    return loaded
