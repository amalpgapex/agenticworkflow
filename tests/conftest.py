"""Shared fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WF_ENV", "dev")
    monkeypatch.setenv("WF_EXECUTOR_MODEL", "test-executor")
    monkeypatch.setenv("WF_EVALUATOR_MODEL", "test-evaluator")
    monkeypatch.setenv("WF_REVIEWER_EMAIL", "reviewer@example.com")
    monkeypatch.setenv("WF_TOKEN_SECRET", "test-secret")
    monkeypatch.setenv("WF_ARTIFACT_BUCKET", "local")
    monkeypatch.setenv("WF_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("WF_SES_SENDER", "sender@example.com")
    os.environ.setdefault("TEMPORAL_ADDRESS", "localhost:7233")
    from wf.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
