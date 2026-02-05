# Copyright (c) Microsoft. All rights reserved.

"""Agent Framework DevUI - Debug interface with OpenAI compatible API server."""

import importlib.metadata
import logging
from typing import Any

from ._conversations import CheckpointConversationManager
from ._cleanup import register_cleanup, _get_registered_cleanup_hooks
from ._server import DevServer
from .models import AgentFrameworkRequest, OpenAIError, OpenAIResponse, ResponseStreamEvent
from .models._discovery_models import DiscoveryResponse, EntityInfo, EnvVarRequirement
from ._utils import create_foundry_agent

logger = logging.getLogger(__name__)

try:
    __version__ = importlib.metadata.version(__name__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback for development mode


def serve(
    entities: list[Any] | None = None,
    entities_dir: str | None = None,
    port: int = 8080,
    host: str = "127.0.0.1",
    cors_origins: list[str] | None = None,
    ui_enabled: bool = True,
    instrumentation_enabled: bool = False,
    mode: str = "developer",
    auth_enabled: bool = False,
    auth_token: str | None = None,
) -> None:
    """Launch Agent Framework DevUI with simple API.

    Args:
        entities: List of entities for in-memory registration (IDs auto-generated)
        entities_dir: Directory to scan for entities
        port: Port to run server on
        host: Host to bind server to
        cors_origins: List of allowed CORS origins
        ui_enabled: Whether to enable the UI
        instrumentation_enabled: Whether to enable OpenTelemetry instrumentation
        mode: Server mode - 'developer' (full access, verbose errors) or 'user' (restricted APIs, generic errors)
        auth_enabled: Whether to enable Bearer token authentication
        auth_token: Custom authentication token (auto-generated if not provided with auth_enabled=True)
    """
    import re

    import uvicorn

    # Validate host parameter early for security
    if not re.match(r"^(localhost|127\.0\.0\.1|0\.0\.0\.0|[a-zA-Z0-9.-]+)$", host):
        raise ValueError(f"Invalid host: {host}. Must be localhost, IP address, or valid hostname")

    # Validate port parameter
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ValueError(f"Invalid port: {port}. Must be integer between 1 and 65535")

    # Security check: Warn if network-exposed without authentication
    if host not in ("127.0.0.1", "localhost") and not auth_enabled:
        logger.warning("⚠️  WARNING: Exposing DevUI to network without authentication!")
        logger.warning("⚠️  This is INSECURE - anyone on your network can access your agents")
        logger.warning("💡 For network exposure, add --auth flag: devui --host 0.0.0.0 --auth")

    # Handle authentication configuration
    if auth_enabled:
        import os
        import secrets

        # Check if token is in environment variable first
        if not auth_token:
            auth_token = os.environ.get("DEVUI_AUTH_TOKEN")

        # Auto-generate token if STILL not provided
        if not auth_token:
            # Check if we're in a production-like environment
            is_production = (
                host not in ("127.0.0.1", "localhost")  # Exposed to network
                or os.environ.get("CI") == "true"  # Running in CI
                or os.environ.get("KUBERNETES_SERVICE_HOST")  # Running in k8s
            )

            if is_production:
                # REFUSE to start without explicit token
                logger.error("❌ Authentication enabled but no token provided")
                logger.error("❌ Auto-generated tokens are NOT secure for network-exposed deployments")
                logger.error("💡 Set token: export DEVUI_AUTH_TOKEN=<your-secure-token>")
                logger.error("💡 Or pass: serve(entities=[...], auth_token='your-token')")
                raise ValueError("DEVUI_AUTH_TOKEN required when host is not localhost")

            # Development mode: auto-generate and show
            auth_token = secrets.token_urlsafe(32)
            logger.info("🔒 Authentication enabled with auto-generated token")
            logger.info("\n" + "=" * 70)
            logger.info("🔑 DEV TOKEN (localhost only, shown once):")
            logger.info(f"   {auth_token}")
            logger.info("=" * 70 + "\n")
        else:
            logger.info("🔒 Authentication enabled with provided token")

        # Set environment variable for server to use
        os.environ["AUTH_REQUIRED"] = "true"
        os.environ["DEVUI_AUTH_TOKEN"] = auth_token

    # Enable instrumentation if requested
    if instrumentation_enabled:
        from agent_framework.observability import enable_instrumentation

        enable_instrumentation(enable_sensitive_data=True)
        logger.info("Enabled Agent Framework instrumentation with sensitive data")

    # Create server with direct parameters
    server = DevServer(
        entities_dir=entities_dir,
        port=port,
        host=host,
        cors_origins=cors_origins,
        ui_enabled=ui_enabled,
        mode=mode,
    )

    # Register in-memory entities if provided
    if entities:
        logger.info(f"Registering {len(entities)} in-memory entities")
        # Store entities for later registration during server startup
        server._pending_entities = entities

    app = server.get_app()

    logger.info(f"Starting Agent Framework DevUI on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


# Export main public API
__all__ = [
    "AgentFrameworkRequest",
    "CheckpointConversationManager",
    "DevServer",
    "DiscoveryResponse",
    "EntityInfo",
    "EnvVarRequirement",
    "OpenAIError",
    "OpenAIResponse",
    "ResponseStreamEvent",
    "register_cleanup",
    "serve",
    "create_foundry_agent",
]


