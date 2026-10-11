"""Jinja2 HTML → WeasyPrint PDF. DOCX is stubbed only (FR-64)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from jinja2 import Environment, FileSystemLoader, select_autoescape

from wf.errors import DeliveryError


class Renderer(Protocol):
    """Output renderer interface."""

    def render(self, context: dict[str, Any]) -> bytes:
        """Render bytes for a given format."""


class DocxRenderer:
    """Phase 1 stub. DOCX is not implemented."""

    def render(self, context: dict[str, Any]) -> bytes:
        del context
        raise DeliveryError("DOCX output is not implemented in Phase 1")


def template_dir() -> Path:
    """Return the project templates directory."""
    return Path(__file__).resolve().parents[3] / "templates"


def render_html(template_name: str, context: dict[str, Any]) -> str:
    """Render a Jinja2 HTML template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir())),
        autoescape=select_autoescape(["html"]),
    )
    return env.get_template(template_name).render(**context)


def render_weather_plan_pdf(context: dict[str, Any]) -> bytes:
    """Render the weather plan HTML to PDF (FR-60, FR-61)."""
    html = render_html("weather_plan.html", context)
    try:
        from weasyprint import HTML
    except ImportError as exc:  # pragma: no cover
        raise DeliveryError("weasyprint is not installed") from exc
    return HTML(string=html, base_url=str(template_dir())).write_pdf()
