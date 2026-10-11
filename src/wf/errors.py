"""Typed errors for the workflow engine."""

from __future__ import annotations


class WfError(Exception):
    """Base error for the wf package."""


class DefinitionError(WfError):
    """A workflow definition failed validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


class ExpressionError(WfError):
    """A CEL expression failed to compile or evaluate."""


class ToolError(WfError):
    """An MCP / Open-Meteo tool returned a typed failure."""


class CheckError(WfError):
    """A named check could not run."""


class DeliveryError(WfError):
    """Email, render, or artifact delivery failed."""


class ConfigError(WfError):
    """Required configuration is missing or invalid."""
