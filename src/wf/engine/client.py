"""Temporal client helpers: start, signal, query."""

from __future__ import annotations

import uuid
from typing import Any

from temporalio.client import Client

from wf.config import get_settings
from wf.definition.models import Definition
from wf.engine.workflow import InterpreterWorkflow, WorkflowInput
from wf.schemas.core import HumanDecision


async def connect() -> Client:
    """Connect to the configured Temporal server."""
    settings = get_settings()
    return await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)


async def start_run(
    definition: Definition,
    inputs: dict[str, Any],
    *,
    initiator: str,
    auto_approve: bool = False,
    run_id: str | None = None,
) -> str:
    """Start InterpreterWorkflow and return the run_id."""
    settings = get_settings()
    client = await connect()
    rid = run_id or f"wf-{uuid.uuid4()}"
    await client.start_workflow(
        InterpreterWorkflow.run,
        WorkflowInput(
            definition_json=definition.model_dump(mode="json", by_alias=True),
            inputs=inputs,
            initiator=initiator,
            run_id=rid,
            auto_approve=auto_approve,
        ),
        id=rid,
        task_queue=settings.temporal_task_queue,
    )
    return rid


async def query_status(run_id: str) -> dict[str, Any]:
    """Query InterpreterWorkflow.status."""
    client = await connect()
    handle = client.get_workflow_handle(run_id)
    result = await handle.query(InterpreterWorkflow.status)
    return result if isinstance(result, dict) else dict(result)


async def signal_decision(run_id: str, decision: HumanDecision) -> None:
    """Send a human_decision signal."""
    client = await connect()
    handle = client.get_workflow_handle(run_id)
    await handle.signal(InterpreterWorkflow.human_decision, decision)
