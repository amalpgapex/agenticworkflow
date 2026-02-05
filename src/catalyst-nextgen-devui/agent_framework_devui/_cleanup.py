# Copyright (c) Microsoft. All rights reserved.

"""Cleanup registry and management for DevUI entities."""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Module-level cleanup registry (before serve() is called)
_cleanup_registry: dict[int, list[Callable[[], Any]]] = {}


def register_cleanup(entity: Any, *hooks: Callable[[], Any]) -> None:
    """Register cleanup hook(s) for an entity.

    Cleanup hooks execute during DevUI server shutdown, before entity
    clients are closed. Supports both synchronous and asynchronous callables.

    Args:
        entity: Agent, workflow, or other entity object
        *hooks: One or more cleanup callables (sync or async)

    Raises:
        ValueError: If no hooks provided

    Examples:
        Single cleanup hook:
        >>> from agent_framework.devui import serve, register_cleanup
        >>> credential = DefaultAzureCredential()
        >>> agent = ChatAgent(...)
        >>> register_cleanup(agent, credential.close)
        >>> serve(entities=[agent])

        Multiple cleanup hooks:
        >>> register_cleanup(agent, credential.close, session.close, db_pool.close)

        Works with file-based discovery:
        >>> # In agents/my_agent/agent.py
        >>> from agent_framework.devui import register_cleanup
        >>> credential = DefaultAzureCredential()
        >>> agent = ChatAgent(...)
        >>> register_cleanup(agent, credential.close)
        >>> # Run: devui ./agents
    """
    if not hooks:
        raise ValueError("At least one cleanup hook required")

    # Use id() to track entity identity (works across modules)
    entity_id = id(entity)

    if entity_id not in _cleanup_registry:
        _cleanup_registry[entity_id] = []

    _cleanup_registry[entity_id].extend(hooks)

    logger.debug(
        f"Registered {len(hooks)} cleanup hook(s) for {type(entity).__name__} "
        f"(id: {entity_id}, total: {len(_cleanup_registry[entity_id])})"
    )


def _get_registered_cleanup_hooks(entity: Any) -> list[Callable[[], Any]]:
    """Get cleanup hooks registered for an entity (internal use).

    Args:
        entity: Entity object to get hooks for

    Returns:
        List of cleanup hooks registered for the entity
    """
    entity_id = id(entity)
    return _cleanup_registry.get(entity_id, [])
