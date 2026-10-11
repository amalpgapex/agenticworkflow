"""Named deterministic checks."""

from wf.checks.registry import CheckResult, get_check, run_named_check
from wf.checks.weather import is_poor_weather_day, is_severe_day

__all__ = ["CheckResult", "get_check", "is_poor_weather_day", "is_severe_day", "run_named_check"]
