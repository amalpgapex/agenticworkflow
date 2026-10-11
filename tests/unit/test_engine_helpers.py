"""Engine helpers used by the interpreter."""

from __future__ import annotations

from wf.engine.activities import json_diff
from wf.engine.worker import run_worker
from wf.engine.workflow import _add_usage, _bind


def test_bind_ctx_location() -> None:
    ctx: dict[str, object] = {}
    _bind(ctx, "ctx.location", {"name": "Lisbon"})
    assert ctx["location"]["name"] == "Lisbon"  # type: ignore[index]


def test_worker_module_exports_run() -> None:
    assert callable(run_worker)


def test_add_usage_and_diff() -> None:
    usage = _add_usage({"input_tokens": 1, "output_tokens": 2}, {"input_tokens": 3, "output_tokens": 4})
    assert usage == {"input_tokens": 4, "output_tokens": 6}
    diff = json_diff({"a": 1}, {"a": 2})
    assert diff["changed"] is True
