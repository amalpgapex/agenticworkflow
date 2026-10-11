"""Typer CLI: validate, run, status."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from wf.config import get_settings
from wf.definition.loader import load_definition, validate_run_inputs
from wf.errors import ConfigError, DefinitionError
from wf.logging import configure_logging, get_logger

app = typer.Typer(name="wf", help="Definition-driven agentic workflow engine.", no_args_is_help=True)


@app.callback()
def _main() -> None:
    """Load `.env` and configure logging for every command."""
    from dotenv import load_dotenv

    load_dotenv()
    configure_logging()


@app.command()
def validate(file: Path) -> None:
    """Validate a workflow definition (FR-05, AC-01)."""
    try:
        definition = load_definition(file)
    except DefinitionError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"ok: {definition.workflow.id}@{definition.workflow.version}")


@app.command()
def run(
    definition: Path,
    initiator: str = typer.Option(..., help="Initiator email"),
    input: list[str] | None = typer.Option(None, help="k=v run input"),
    auto_approve: bool = typer.Option(False, help="Skip HITL (WF_ENV=dev only)"),
) -> None:
    """Validate, start a Temporal run, and print the run_id (FR-70)."""
    settings = get_settings()
    if auto_approve and not settings.auto_approve_allowed():
        typer.echo("--auto-approve is refused unless WF_ENV=dev", err=True)
        raise typer.Exit(code=2)
    raw_inputs = _parse_kv(input or [])
    try:
        loaded = load_definition(definition)
        run_inputs = validate_run_inputs(loaded, raw_inputs)
    except DefinitionError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    from wf.engine.client import start_run

    run_id = asyncio.run(
        start_run(
            loaded,
            run_inputs,
            initiator=initiator,
            auto_approve=auto_approve,
        )
    )
    get_logger().info("run_started")
    typer.echo(run_id)


@app.command()
def status(run_id: str) -> None:
    """Show the current step and any pending human decision (FR-18)."""
    from wf.engine.client import query_status

    try:
        payload = asyncio.run(query_status(run_id))
    except Exception as exc:  # noqa: BLE001
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(payload)


def _parse_kv(pairs: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise typer.BadParameter(f"expected k=v, got {item!r}")
        key, value = item.split("=", 1)
        result[key] = value
    return result


def main() -> None:
    """Console-script entry point."""
    try:
        app()
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise SystemExit(1) from exc
