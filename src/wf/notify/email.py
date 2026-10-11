"""SES raw MIME email (attachments)."""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from wf.config import get_settings
from wf.errors import DeliveryError


def email_template_dir() -> Path:
    """Return the directory of HTML email templates."""
    return Path(__file__).resolve().parents[3] / "templates" / "email"


def send_html_email(
    *,
    to_addresses: list[str],
    subject: str,
    html: str,
    attachments: list[dict[str, Any]] | None = None,
) -> None:
    """Send a raw MIME email via SES. Fail fast if the sender is unverified."""
    settings = get_settings()
    sender = settings.require_ses_sender()
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(to_addresses)
    message["Subject"] = subject
    message.set_content("This message requires an HTML client.")
    message.add_alternative(html, subtype="html")
    for item in attachments or []:
        message.add_attachment(
            item["content"],
            maintype="application",
            subtype="pdf",
            filename=item.get("filename") or "attachment.pdf",
        )
    client = boto3.client("ses", region_name=settings.aws_region)
    try:
        client.send_raw_email(
            Source=sender,
            Destinations=to_addresses,
            RawMessage={"Data": message.as_bytes()},
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"MessageRejected", "MailFromDomainNotVerified", "ConfigurationSetDoesNotExist"}:
            if settings.wf_env == "dev":
                # Sandbox accounts cannot mail unverified recipients. Local
                # --auto-approve runs still persist the PDF (FR-71).
                from wf.logging import get_logger

                get_logger().warning("ses_skipped_unverified", region=settings.aws_region)
                return
            raise DeliveryError(f"SES sender or recipient is not verified: {exc}") from exc
        raise DeliveryError(f"SES send failed: {exc}") from exc
