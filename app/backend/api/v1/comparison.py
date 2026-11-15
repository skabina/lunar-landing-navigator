from fastapi import APIRouter

from app.backend.api.v1.analysis import analyze_site
from app.backend.schemas.comparison import (
    CompareRequest,
    CompareResponse,
    ComparisonScenario,
    ScenarioDelta,
)

router = APIRouter(tags=["comparison"])


@router.post("/compare", response_model=CompareResponse)
def compare_sites(request: CompareRequest) -> CompareResponse:
    analyses = [analyze_site(scenario) for scenario in request.scenarios]
    baseline = analyses[0].metrics
    scenarios: list[ComparisonScenario] = []
    for index, analysis in enumerate(analyses):
        metrics = analysis.metrics
        delta = None if index == 0 else ScenarioDelta(
            illumination_pct=metrics.illumination_pct - baseline.illumination_pct,
            comm_pct=metrics.comm_pct - baseline.comm_pct,
            longest_dark_hours=metrics.longest_dark_hours - baseline.longest_dark_hours,
            score=analysis.score.total - analyses[0].score.total,
        )
        scenarios.append(
            ComparisonScenario(
                label=f"Scenario {index + 1}",
                analysis=analysis,
                deltas=delta,
            )
        )
    best = max(scenarios, key=lambda scenario: scenario.analysis.score.total)
    sources = ", ".join(
        f"{scenario.label}: {scenario.analysis.data_source}"
        for scenario in scenarios
    )
    fallback_count = sum(
        scenario.analysis.data_source == "fallback" for scenario in scenarios
    )
    quality_note = (
        f" {fallback_count} scenario(s) use deterministic fallback data."
        if fallback_count
        else ""
    )
    return CompareResponse(
        scenarios=scenarios,
        summary=(
            f"{best.label} has the highest current decision-support score "
            f"({best.analysis.score.total:.1f}/100). Results may combine NASA, "
            f"cache, or fallback data; sources: {sources}.{quality_note}"
        ),
    )
