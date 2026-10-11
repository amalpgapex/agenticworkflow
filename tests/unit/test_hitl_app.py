"""AC-07 review app rejects bad accounts and stale tokens."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from wf.hitl.app import create_app
from wf.hitl.auth import email_allowed
from wf.hitl.tokens import sign_review_token


def test_stale_token_rejected() -> None:
    app = create_app()
    client = TestClient(app)
    token = sign_review_token(run_id="wf-1", step_id="create_plan", attempt=1, nonce="n1", max_age=1)
    with patch("wf.hitl.app.load_review_token", side_effect=ValueError("stale token")):
        response = client.get(f"/review/{token}")
    assert response.status_code == 400


def test_non_allowlisted_account_rejected() -> None:
    """AC-07: a Google account outside reviewers cannot decide."""
    assert email_allowed("intruder@gmail.com", ["reviewer@example.com"], True) is False
    app = create_app()
    token = sign_review_token(run_id="wf-1", step_id="create_plan", attempt=1, nonce="n1", max_age=3600)
    status = {
        "run_id": "wf-1",
        "reviewers": ["reviewer@example.com"],
        "pending_human": True,
        "attempt": 1,
        "nonce": "n1",
        "data": {},
        "eval": {"verdict": "pass", "score": 1},
        "checks": [],
        "current_step": "create_plan",
        "schema_name": "ActivityPlan@1",
    }
    with (
        patch("wf.hitl.app.query_status", new=AsyncMock(return_value=status)),
        patch("wf.hitl.app.signal_decision", new=AsyncMock()) as signal,
        TestClient(app) as client,
    ):
        response = client.post(
            f"/review/{token}",
            data={
                "action": "proceed",
                "csrf": "abc",
                "feedback": "",
                "modified_json": "",
            },
        )
    assert response.status_code in {403, 400, 409}
    signal.assert_not_called()
