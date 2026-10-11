"""Environment-driven settings (REQUIREMENTS §4)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from wf.errors import ConfigError


class Settings(BaseSettings):
    """Runtime configuration loaded from the environment or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    wf_env: Literal["dev", "test"] = "dev"
    aws_region: str = "us-east-1"
    wf_executor_model: str = "bedrock:us.anthropic.claude-sonnet-4-6"
    wf_evaluator_model: str = "bedrock:us.anthropic.claude-sonnet-4-6"
    wf_agent_max_requests: int = 20
    wf_agent_max_tokens: int = 20000
    wf_artifact_bucket: str = "local"
    wf_ses_sender: str = ""
    wf_reviewer_email: str = "reviewer@example.com"
    wf_review_base_url: str = "http://localhost:8000"
    wf_token_secret: str = "dev-only-change-me"
    google_client_id: str = ""
    google_client_secret: str = ""
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "wf-task-queue"
    wf_presign_expiry_seconds: int = 604800
    artifact_root: str = Field(default="artifacts", alias="WF_ARTIFACT_ROOT")

    @field_validator("wf_token_secret")
    @classmethod
    def token_secret_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ConfigError("WF_TOKEN_SECRET is required and must not be empty")
        return value

    def require_ses_sender(self) -> str:
        """Return the SES sender or raise if it is unset."""
        if not self.wf_ses_sender.strip():
            raise ConfigError("WF_SES_SENDER is required for email delivery")
        return self.wf_ses_sender

    def require_google(self) -> tuple[str, str]:
        """Return Google OAuth credentials or raise if they are unset."""
        if not self.google_client_id.strip() or not self.google_client_secret.strip():
            raise ConfigError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required for the review app")
        return self.google_client_id, self.google_client_secret

    def auto_approve_allowed(self) -> bool:
        """Return whether `--auto-approve` is permitted."""
        return self.wf_env == "dev"

    def uses_local_artifacts(self) -> bool:
        """Return whether artifacts are written to the local filesystem."""
        return self.wf_artifact_bucket == "local"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load `.env` into the process environment, then cache settings.

    Boto3 (Bedrock, SES, S3) reads `AWS_REGION` / `AWS_PROFILE` from
    `os.environ`, not from the Settings object, so dotenv must run first.
    """
    from dotenv import load_dotenv

    load_dotenv()
    return Settings()
