"""Google OIDC via authlib (FR-52)."""

from __future__ import annotations

from authlib.integrations.starlette_client import OAuth

from wf.config import get_settings

GOOGLE_DISCOVERY = "https://accounts.google.com/.well-known/openid-configuration"


def build_oauth() -> OAuth:
    """Configure the Google OAuth client."""
    settings = get_settings()
    client_id, client_secret = settings.require_google()
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url=GOOGLE_DISCOVERY,
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


def email_allowed(email: str, reviewers: list[str], email_verified: bool) -> bool:
    """Return True if the Google account may decide (FR-52)."""
    if not email_verified:
        return False
    allowed = {item.lower() for item in reviewers}
    return email.lower() in allowed
