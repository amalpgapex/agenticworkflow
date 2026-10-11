"""M0 config and CLI help."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from wf.cli import app
from wf.config import get_settings
from wf.definition.models import parse_duration
from wf.errors import DefinitionError


def test_help() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "validate" in result.stdout
    assert "run" in result.stdout


def test_settings_defaults() -> None:
    settings = get_settings()
    assert settings.wf_artifact_bucket == "local"
    assert settings.wf_agent_max_requests == 20
    assert settings.auto_approve_allowed() is True


def test_parse_duration() -> None:
    assert parse_duration("72h").total_seconds() == 72 * 3600
    assert parse_duration("30m").total_seconds() == 1800
    assert parse_duration("15s").total_seconds() == 15
    try:
        parse_duration("2d")
        raise AssertionError("expected DefinitionError")
    except DefinitionError:
        pass


def test_auto_approve_refused_in_test(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WF_ENV", "test")
    get_settings.cache_clear()
    result = CliRunner().invoke(
        app,
        ["run", "definitions/weather_plan.yaml", "--initiator", "a@b.c", "--auto-approve"],
    )
    assert result.exit_code == 2
    get_settings.cache_clear()
