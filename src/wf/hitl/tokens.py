"""Signed, expiring review tokens (FR-51)."""

from __future__ import annotations

from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from wf.config import get_settings


def _serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.wf_token_secret, salt="wf-review")


def sign_review_token(
    *,
    run_id: str,
    step_id: str,
    attempt: int,
    nonce: str,
    max_age: int,
) -> str:
    """Create a signed token. `max_age` is stored for the caller; expiry is checked on load."""
    del max_age
    return _serializer().dumps({"run_id": run_id, "step_id": step_id, "attempt": attempt, "nonce": nonce})


def load_review_token(token: str, max_age: int) -> dict[str, Any]:
    """Load and validate a review token. Raise ValueError if stale or invalid."""
    try:
        payload = _serializer().loads(token, max_age=max_age)
    except SignatureExpired as exc:
        raise ValueError("stale token") from exc
    except BadSignature as exc:
        raise ValueError("invalid token") from exc
    if not isinstance(payload, dict):
        raise ValueError("invalid token")
    return payload
