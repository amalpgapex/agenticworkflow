"""Local artifacts and HTML render."""

from __future__ import annotations

from pathlib import Path

from wf.render.pdf import render_html
from wf.storage.artifacts import LocalArtifactStore


def test_local_artifact_roundtrip(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)
    uri = store.put_text("runs/wf-1/steps/a.json", '{"ok": true}')
    assert uri.startswith("file://")
    assert b"ok" in store.get_bytes("runs/wf-1/steps/a.json")
    assert store.presign("runs/wf-1/steps/a.json", 60).endswith("a.json")


def test_weather_plan_html_contains_attribution() -> None:
    html = render_html(
        "weather_plan.html",
        {
            "run_id": "wf-1",
            "forecast": {
                "location": {
                    "name": "Lisbon",
                    "country": "Portugal",
                    "country_code": "PT",
                    "timezone": "Europe/Lisbon",
                },
                "days": [
                    {
                        "date": "2026-10-07",
                        "weather_description": "Clear sky",
                        "weather_code": 0,
                        "temp_max_c": 22,
                        "temp_min_c": 14,
                        "precipitation_mm": 0,
                        "precipitation_probability_max": 5,
                        "wind_speed_max_kmh": 10,
                    }
                ],
            },
            "advisory": None,
            "plan": {
                "location_name": "Lisbon",
                "days": [
                    {
                        "date": "2026-10-07",
                        "outdoor_suitability": "good",
                        "weather_summary": "sun",
                        "morning": "walk",
                        "afternoon": "museum",
                        "evening": "dinner",
                        "indoor_alternative": "",
                        "packing": [],
                    }
                ],
                "general_tips": ["water"],
            },
            "approval": {"decision": "proceed", "reviewer": "auto", "decided_at": "now"},
        },
    )
    assert "Weather data by Open-Meteo.com (CC BY 4.0)" in html
    assert "wf-1" in html
    assert "Lisbon" in html
