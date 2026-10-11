"""Activity helpers and persistence (engine coverage)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from wf.engine import activities
from wf.engine.client import query_status, signal_decision, start_run
from wf.schemas.core import Envelope, HumanDecision, SystemMeta


@pytest.mark.asyncio
async def test_evaluate_and_map_input() -> None:
    assert await activities.evaluate_expression("1 + 1", {}) == 2
    mapped = await activities.map_step_input(
        {"days": "inputs.days"},
        {"inputs": {"days": 7}, "ctx": {}, "steps": {}},
    )
    assert mapped["days"] == 7


@pytest.mark.asyncio
async def test_run_checks_activity() -> None:
    day = {
        "date": "2026-10-07",
        "weather_code": 0,
        "weather_description": "Clear sky",
        "temp_max_c": 20.0,
        "temp_min_c": 10.0,
        "precipitation_mm": 0.0,
        "precipitation_probability_max": 5.0,
        "wind_speed_max_kmh": 12.0,
    }
    results = await activities.run_checks_activity(
        {
            "data": {"days": [day]},
            "context": {"inputs": {"days": 1}, "ctx": {}, "steps": {}},
            "tool_trace": [{"tool_name": "get_daily_forecast", "args": {}, "return_value": {"days": [day]}}],
            "cel_checks": ["size(data.days) == inputs.days"],
            "named_checks": ["forecast_matches_source"],
        }
    )
    assert results[0]["passed"] is True
    assert results[1]["passed"] is True


@pytest.mark.asyncio
async def test_persist_envelope(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WF_ARTIFACT_ROOT", str(tmp_path))
    from wf.config import get_settings

    get_settings.cache_clear()
    envelope = Envelope(
        system=SystemMeta(
            run_id="wf-1",
            workflow_id="weather-plan",
            definition_version="0.1.0",
            step_id="create_plan",
            status="completed",
        ),
        data={"ok": True},
    )
    uri = await activities.persist_envelope_activity({"envelope": envelope.model_dump(mode="json")})
    assert "wf-1" in uri


@pytest.mark.asyncio
async def test_validate_modified_data() -> None:
    loc = {
        "name": "Lisbon",
        "latitude": 1,
        "longitude": 2,
        "country": "Portugal",
        "country_code": "PT",
        "feature_code": "PPLC",
        "timezone": "Europe/Lisbon",
    }
    data = await activities.validate_modified_data_activity(
        {
            "schema_name": "ResolvedLocation@1",
            "data": loc,
        }
    )
    assert data["name"] == "Lisbon"


@pytest.mark.asyncio
async def test_client_helpers() -> None:
    handle = MagicMock()
    client = MagicMock()
    client.get_workflow_handle = MagicMock(return_value=handle)

    async def _start(*args: Any, **kwargs: Any) -> None:
        return None

    async def _query(*args: Any, **kwargs: Any) -> dict[str, str]:
        return {"status": "running"}

    async def _signal(*args: Any, **kwargs: Any) -> None:
        return None

    async def _connect() -> MagicMock:
        return client

    client.start_workflow = _start
    handle.query = _query
    handle.signal = _signal
    from pathlib import Path

    from wf.definition.loader import load_definition

    definition = load_definition(Path("definitions/weather_plan.yaml"))
    with patch("wf.engine.client.connect", _connect):
        run_id = await start_run(definition, {"country": "PT"}, initiator="a@b.c")
        assert run_id.startswith("wf-")
        status = await query_status(run_id)
        assert status["status"] == "running"
        await signal_decision(
            run_id,
            HumanDecision(action="proceed", reviewer="r", attempt=1, nonce="n"),
        )
