from pydantic import BaseModel, Field


class Metrics(BaseModel):
    illumination_pct: float = Field(ge=0, le=100)
    comm_pct: float = Field(ge=0, le=100)
    sun_elevation_max_deg: float
    sun_elevation_mean_deg: float
    longest_dark_hours: float = Field(ge=0)
    longest_comm_outage_hours: float = Field(ge=0)
    n_dark_periods: int = Field(ge=0)
    n_comm_outages: int = Field(ge=0)
    time_to_sunset_hours: float | None = Field(default=None, ge=0)
    time_to_earthset_hours: float | None = Field(default=None, ge=0)
    overlap_pct: float = Field(ge=0, le=100)


class ScoreBreakdown(BaseModel):
    power: float = Field(ge=0, le=100)
    communication: float = Field(ge=0, le=100)
    survivability: float = Field(ge=0, le=100)
    total: float = Field(ge=0, le=100)
