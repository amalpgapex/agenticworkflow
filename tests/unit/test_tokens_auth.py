"""FR-51, FR-52 tokens and allowlist."""

from __future__ import annotations

import pytest

from wf.hitl.auth import email_allowed
from wf.hitl.tokens import load_review_token, sign_review_token


def test_token_roundtrip() -> None:
    token = sign_review_token(run_id="wf-1", step_id="create_plan", attempt=1, nonce="n1", max_age=3600)
    payload = load_review_token(token, max_age=3600)
    assert payload["run_id"] == "wf-1"
    assert payload["nonce"] == "n1"


def test_stale_token() -> None:
    token = sign_review_token(run_id="wf-1", step_id="create_plan", attempt=1, nonce="n1", max_age=1)
    with pytest.raises(ValueError, match="invalid"):
        load_review_token(token + "tampered", max_age=3600)


def test_email_allowlist_case_insensitive() -> None:
    assert email_allowed("Reviewer@Example.com", ["reviewer@example.com"], True)
    assert email_allowed("other@example.com", ["reviewer@example.com"], True) is False
    assert email_allowed("reviewer@example.com", ["reviewer@example.com"], False) is False
