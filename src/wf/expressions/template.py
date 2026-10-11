"""`${...}` interpolation. Each placeholder is a CEL expression."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from wf.expressions.cel import evaluate_cel

_PLACEHOLDER = re.compile(r"\$\{([^{}]+)\}")


def iter_placeholders(text: str) -> Iterator[str]:
    """Yield the CEL source of each `${...}` placeholder."""
    for match in _PLACEHOLDER.finditer(text):
        yield match.group(1).strip()


def interpolate(text: str, context: dict[str, Any], *, roots: frozenset[str] | None = None) -> str:
    """Replace `${...}` placeholders. If `roots` is set, other placeholders are left intact."""

    def repl(match: re.Match[str]) -> str:
        expr = match.group(1).strip()
        root = expr.split(".", 1)[0]
        if roots is not None and root not in roots:
            return match.group(0)
        result = evaluate_cel(expr, context)
        if result is None:
            return ""
        return str(result)

    return _PLACEHOLDER.sub(repl, text)
