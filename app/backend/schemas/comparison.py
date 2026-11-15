from pydantic import BaseModel, Field

from app.backend.schemas.analysis import AnalysisResponse, AnalyzeRequest


class CompareRequest(BaseModel):
    scenarios: list[AnalyzeRequest] = Field(
        min_length=2,
        max_length=3,
        examples=[
            [
                {
                    "site_id": "shackleton-rim",
                    "start_utc": "2026-01-01T00:00:00Z",
                    "duration_days": 14,
                    "step_minutes": 30,
                },
                {
                    "site_id": "malapert-massif",
                    "start_utc": "2026-01-15T00:00:00Z",
                    "duration_days": 14,
                    "step_minutes": 30,
                },
            ]
        ],
    )


class ScenarioDelta(BaseModel):
    illumination_pct: float
    comm_pct: float
    longest_dark_hours: float
    score: float


class ComparisonScenario(BaseModel):
    label: str
    analysis: AnalysisResponse
    deltas: ScenarioDelta | None = None


class CompareResponse(BaseModel):
    scenarios: list[ComparisonScenario]
    summary: str
