from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.backend.schemas.metrics import Metrics, ScoreBreakdown
from app.backend.schemas.site import Site


class AnalyzeRequest(BaseModel):
    site_id: str | None = Field(default=None, examples=["shackleton-rim"])
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    start_utc: datetime = Field(
        examples=["2026-01-01T00:00:00Z"],
    )
    duration_days: int = Field(default=14, ge=1, le=90)
    step_minutes: int = Field(default=30, ge=1, le=1440)
    antenna_height_m: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def require_site_or_coordinates(self) -> "AnalyzeRequest":
        if not self.site_id and (self.lat is None or self.lon is None):
            raise ValueError("Provide site_id or both lat and lon")
        return self


class TimeSeries(BaseModel):
    t: list[datetime]
    sun_az: list[float]
    sun_el: list[float]
    earth_az: list[float]
    earth_el: list[float]


class Interval(BaseModel):
    start: datetime
    end: datetime


class AnalysisResponse(BaseModel):
    site: Site
    request: AnalyzeRequest
    timeseries: TimeSeries
    horizon_mask_deg: list[float] = Field(min_length=360, max_length=360)
    sun_intervals: list[Interval]
    earth_intervals: list[Interval]
    dark_intervals: list[Interval]
    metrics: Metrics
    score: ScoreBreakdown
    terrain_source: str
    data_source: str = "fallback"
    data_quality: str = "fallback"
    warnings: list[str] = Field(default_factory=list)
    cached: bool = False
