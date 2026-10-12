"""Temporal worker process."""

from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from wf.config import get_settings
from wf.engine import activities
from wf.engine.workflow import InterpreterWorkflow
from wf.logging import configure_logging, get_logger


async def run_worker() -> None:
    """Poll the configured task queue."""
    configure_logging()
    settings = get_settings()
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[InterpreterWorkflow],
        # Pydantic/beartype circular-import under the default sandbox (NFR-02
        # still applies in workflow.py: no I/O, time, or randomness there).
        workflow_runner=UnsandboxedWorkflowRunner(),
        activities=[
            activities.evaluate_expression,
            activities.map_step_input,
            activities.run_resolver_activity,
            activities.run_executor_activity,
            activities.run_action_activity,  # For type: action steps
            activities.run_checks_activity,
            activities.run_evaluator_activity,
            activities.persist_envelope_activity,
            activities.send_review_email_activity,
            activities.send_notification_activity,
            activities.render_and_deliver_activity,
            activities.validate_modified_data_activity,
        ],
    )
    get_logger().info("worker_started", task_queue=settings.temporal_task_queue)
    await worker.run()


def main() -> None:
    """Console entry for the worker."""
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
