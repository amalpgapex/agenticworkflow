"""AC-01 / FR-01..FR-05: definition loader."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from wf.cli import app
from wf.definition.loader import load_definition, validate_run_inputs
from wf.errors import DefinitionError

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "definitions" / "weather_plan.yaml"
INVALID = ROOT / "tests" / "fixtures" / "invalid"


def test_validate_demo_definition() -> None:
    """FR-05 / AC-01: the demo definition loads."""
    definition = load_definition(DEMO)
    assert definition.workflow.id == "weather-plan"
    assert [step.id for step in definition.steps] == [
        "get_forecast",
        "safety_advisory",
        "create_plan",
    ]


def test_cli_validate_ok() -> None:
    """FR-05: wf validate exits 0."""
    result = CliRunner().invoke(app, ["validate", str(DEMO)])
    assert result.exit_code == 0
    assert "weather-plan" in result.stdout


@pytest.mark.parametrize(
    ("name", "needle"),
    [
        ("duplicate_ids.yaml", "duplicate step id"),
        ("unknown_schema.yaml", "unknown schema"),
        ("unknown_check.yaml", "unknown check"),
        ("unknown_tool.yaml", "unknown tool"),
        ("bad_cel.yaml", "CEL"),
        ("bad_placeholder_root.yaml", "not allowed"),
        ("parallel_type.yaml", "not supported in Phase 1"),
        ("extra_key.yaml", "Extra inputs"),
    ],
)
def test_invalid_fixtures_report_path(name: str, needle: str) -> None:
    """AC-01 / FR-02: each invalid fixture fails with a YAML path."""
    result = CliRunner().invoke(app, ["validate", str(INVALID / name)])
    assert result.exit_code != 0
    assert needle.lower() in result.output.lower()


def test_run_inputs_defaults_and_bounds() -> None:
    """FR-03: run inputs are coerced and bounded."""
    definition = load_definition(DEMO)
    values = validate_run_inputs(definition, {"country": "PT"})
    assert values["city"] == ""
    assert values["days"] == 7
    with pytest.raises(DefinitionError, match="days"):
        validate_run_inputs(definition, {"country": "PT", "days": 99})
    with pytest.raises(DefinitionError, match="required"):
        validate_run_inputs(definition, {})
