"""FastAPI review app: Google OIDC, CSRF, Temporal signal."""

from __future__ import annotations

import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from wf.config import get_settings
from wf.definition.models import parse_duration
from wf.engine.client import query_status, signal_decision
from wf.hitl.auth import build_oauth, email_allowed
from wf.hitl.tokens import load_review_token
from wf.schemas.core import HumanDecision
from wf.schemas.registry import get_schema

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def create_app() -> FastAPI:
    """Build the review FastAPI application."""
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            app.state.oauth = build_oauth()
        except Exception:  # noqa: BLE001
            app.state.oauth = None
        yield

    app = FastAPI(title="wf review", lifespan=lifespan)
    app.state.oauth = None
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.wf_token_secret,
        https_only=False,
        same_site="lax",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/auth/login")
    async def login(request: Request) -> Any:
        oauth = getattr(request.app.state, "oauth", None)
        if oauth is None:
            raise HTTPException(503, "Google OAuth is not configured")
        redirect = str(request.url_for("auth_callback"))
        return await oauth.google.authorize_redirect(request, redirect)

    @app.get("/auth/callback", name="auth_callback")
    async def auth_callback(request: Request) -> RedirectResponse:
        oauth = getattr(request.app.state, "oauth", None)
        if oauth is None:
            raise HTTPException(503, "Google OAuth is not configured")
        token = await oauth.google.authorize_access_token(request)
        user = token.get("userinfo") or {}
        request.session["email"] = user.get("email") or ""
        request.session["email_verified"] = bool(user.get("email_verified"))
        nxt = request.session.pop("next", "/")
        return RedirectResponse(nxt)

    @app.get("/review/{token}", response_class=HTMLResponse)
    async def review_get(request: Request, token: str) -> Any:
        payload = _load_token(token)
        status = await query_status(payload["run_id"])
        email = request.session.get("email")
        if not email:
            request.session["next"] = str(request.url)
            return RedirectResponse(request.url_for("login"))
        if not email_allowed(email, status.get("reviewers") or [], bool(request.session.get("email_verified"))):
            raise HTTPException(403, "account is not an allowlisted reviewer")
        csrf = secrets.token_urlsafe(16)
        request.session["csrf"] = csrf
        return templates.TemplateResponse(
            request,
            "review.html",
            {
                "status": status,
                "token": token,
                "csrf": csrf,
                "email": email,
                "output_json": json.dumps(status.get("data") or {}, indent=2, default=str),
            },
        )

    @app.post("/review/{token}")
    async def review_post(
        request: Request,
        token: str,
        action: str = Form(...),
        csrf: str = Form(...),
        feedback: str = Form(""),
        modified_json: str = Form(""),
    ) -> Any:
        if csrf != request.session.get("csrf"):
            raise HTTPException(403, "invalid CSRF token")
        payload = _load_token(token)
        status = await query_status(payload["run_id"])
        email = str(request.session.get("email") or "")
        if not email_allowed(email, status.get("reviewers") or [], bool(request.session.get("email_verified"))):
            raise HTTPException(403, "account is not an allowlisted reviewer")
        if not status.get("pending_human"):
            raise HTTPException(409, "no pending gate")
        if payload["nonce"] != status.get("nonce") or payload["attempt"] != status.get("attempt"):
            raise HTTPException(409, "stale or reused token")
        modified: dict[str, Any] | None = None
        if action == "proceed_modified":
            try:
                modified = json.loads(modified_json)
            except json.JSONDecodeError as exc:
                raise HTTPException(400, f"invalid JSON: {exc}") from exc
            schema = get_schema(str(status.get("schema_name") or ""))
            if schema is None:
                raise HTTPException(400, "unknown schema")
            try:
                modified = schema.model_validate(modified).model_dump(mode="json")
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(400, f"field errors: {exc}") from exc
        if action == "redo" and not feedback.strip():
            raise HTTPException(400, "feedback is required for redo")
        decision = HumanDecision(
            action=action,  # type: ignore[arg-type]
            reviewer=email,
            attempt=int(payload["attempt"]),
            nonce=str(payload["nonce"]),
            feedback=feedback or None,
            modified_data=modified,
        )
        await signal_decision(payload["run_id"], decision)
        request.session.pop("csrf", None)
        return HTMLResponse("<p>Decision recorded.</p>")

    return app


def _load_token(token: str) -> dict[str, Any]:
    try:
        max_age = int(parse_duration("72h").total_seconds())
        return load_review_token(token, max_age=max_age)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


app = create_app()


def main() -> None:
    """Run the review app with uvicorn."""
    import uvicorn

    uvicorn.run("wf.hitl.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
