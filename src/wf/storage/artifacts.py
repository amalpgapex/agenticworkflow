"""S3 and local filesystem artifact backends."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError

from wf.config import Settings, get_settings
from wf.errors import DeliveryError


class ArtifactStore(Protocol):
    """Store and fetch run artifacts."""

    def put_bytes(self, key: str, body: bytes, content_type: str = "application/octet-stream") -> str:
        """Write bytes and return a URI."""

    def get_bytes(self, key: str) -> bytes:
        """Read bytes for a key."""

    def put_text(self, key: str, text: str) -> str:
        """Write UTF-8 text."""

    def presign(self, key: str, expiry_seconds: int) -> str:
        """Return a download URL or local path."""


class LocalArtifactStore:
    """Filesystem backend used when `WF_ARTIFACT_BUCKET=local`."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise DeliveryError(f"invalid artifact key {key!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def put_bytes(self, key: str, body: bytes, content_type: str = "application/octet-stream") -> str:
        del content_type
        path = self._path(key)
        path.write_bytes(body)
        return f"file://{path}"

    def get_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def put_text(self, key: str, text: str) -> str:
        return self.put_bytes(key, text.encode("utf-8"), "application/json")

    def presign(self, key: str, expiry_seconds: int) -> str:
        del expiry_seconds
        return str(self._path(key))


class S3ArtifactStore:
    """S3 backend."""

    def __init__(self, bucket: str, region: str) -> None:
        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region)

    def put_bytes(self, key: str, body: bytes, content_type: str = "application/octet-stream") -> str:
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=body, ContentType=content_type)
        except ClientError as exc:
            raise DeliveryError(f"S3 put failed: {exc}") from exc
        return f"s3://{self.bucket}/{quote(key)}"

    def get_bytes(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            raise DeliveryError(f"S3 get failed: {exc}") from exc
        return response["Body"].read()

    def put_text(self, key: str, text: str) -> str:
        return self.put_bytes(key, text.encode("utf-8"), "application/json")

    def presign(self, key: str, expiry_seconds: int) -> str:
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expiry_seconds,
            )
        except ClientError as exc:
            raise DeliveryError(f"S3 presign failed: {exc}") from exc


def get_artifact_store(settings: Settings | None = None) -> ArtifactStore:
    """Return the configured artifact store."""
    settings = settings or get_settings()
    if settings.uses_local_artifacts():
        return LocalArtifactStore(Path(settings.artifact_root))
    return S3ArtifactStore(settings.wf_artifact_bucket, settings.aws_region)
