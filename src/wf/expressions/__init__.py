"""CEL compilation/evaluation and ${...} interpolation."""

from wf.expressions.cel import compile_cel, evaluate_cel
from wf.expressions.template import interpolate, iter_placeholders

__all__ = ["compile_cel", "evaluate_cel", "interpolate", "iter_placeholders"]
