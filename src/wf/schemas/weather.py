"""Demo weather schemas (`Name@version`)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ForbidModel(BaseModel):
    """Reject unknown keys."""

    model_config = ConfigDict(extra="forbid")


class ResolvedLocation(ForbidModel):
    """A single geocoded place."""

    name: str
    latitude: float
    longitude: float
    country: str
    country_code: str
    feature_code: str
    timezone: str = "auto"


class ForecastDay(ForbidModel):
    """One forecast day in the `WeatherReport@1` shape."""

    date: date
    weather_code: int
    weather_description: str
    temp_max_c: float
    temp_min_c: float
    precipitation_mm: float
    precipitation_probability_max: float
    wind_speed_max_kmh: float


class WeatherReport(ForbidModel):
    """Forecast for a resolved location."""

    location: ResolvedLocation
    days: list[ForecastDay]
    summary: str


class SevereDay(ForbidModel):
    """One severe day in a safety advisory."""

    date: date
    hazards: list[str]
    advice: str


class SafetyAdvisory(ForbidModel):
    """Safety notes for severe weather."""

    severe_days: list[SevereDay]
    general_advice: str


class PlanDay(ForbidModel):
    """One day of a visitor activity plan."""

    date: date
    weather_summary: str
    outdoor_suitability: Literal["good", "fair", "poor"]
    morning: str
    afternoon: str
    evening: str
    indoor_alternative: str = ""
    packing: list[str] = Field(default_factory=list)


class ActivityPlan(ForbidModel):
    """A day-by-day visitor plan."""

    location_name: str
    days: list[PlanDay]
    general_tips: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
