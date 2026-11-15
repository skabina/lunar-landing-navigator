from fastapi import APIRouter, HTTPException, status

from app.backend.api.v1.sites import PRESETS
from app.backend.integrations.horizons import HorizonsClient
from app.backend.integrations.terrain import load_horizon_mask
from app.backend.schemas.analysis import AnalysisResponse, AnalyzeRequest, Interval, TimeSeries
from app.backend.schemas.metrics import Metrics, ScoreBreakdown
from app.backend.schemas.site import Site
from app.backend.services.analysis_service import get_sun_earth_series
from app.backend.services.analysis_service import calculate_visibility
from app.config import get_settings

router = APIRouter(tags=["analysis"])


def _resolve_site(request: AnalyzeRequest) -> Site:
    if request.site_id:
        for site in PRESETS:
            if site.id == request.site_id:
                return site
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "detail": f"Unknown site_id: {request.site_id}",
                "code": "unknown_site_id",
            },
        )
    return Site(
        id="custom",
        name="Custom site",
        lat=request.lat or 0,
        lon=request.lon or 0,
        description="User-provided coordinates.",
        science_value="Custom analysis",
    )


@router.post("/analyze-site", response_model=AnalysisResponse)
def analyze_site(request: AnalyzeRequest) -> AnalysisResponse:
    site = _resolve_site(request)
    settings = get_settings()
    client = HorizonsClient(settings.horizons_url, settings.cache_dir)
    sun, earth, cached, data_source, data_quality = get_sun_earth_series(
        client,
        lat_deg=site.lat,
        lon_deg=site.lon,
        site_id=site.id,
        start_utc=request.start_utc,
        duration_days=request.duration_days,
        step_minutes=request.step_minutes,
    )
    count = min(len(sun), len(earth))
    sun = sun[:count]
    earth = earth[:count]
    times = [point.timestamp for point in sun]
    sun_az = [point.azimuth_deg for point in sun]
    sun_el = [point.elevation_deg for point in sun]
    earth_az = [point.azimuth_deg for point in earth]
    earth_el = [point.elevation_deg for point in earth]
    horizon_mask, terrain_source = load_horizon_mask(site.id)
    visibility = calculate_visibility(
        sun=sun,
        earth=earth,
        horizon_mask_deg=horizon_mask,
    )

    def as_intervals(values: list[tuple]) -> list[Interval]:
        return [Interval(start=start, end=end) for start, end in values]

    metrics = Metrics(**visibility["metrics"])
    score = ScoreBreakdown(**visibility["score"])
    warnings: list[str] = []
    if data_source == "fallback":
        warnings.append(
            "NASA Horizons data was unavailable or invalid; deterministic offline "
            "fallback data is being shown."
        )
    elif data_source == "cache":
        warnings.append("Using validated cached Horizons data.")
    elif data_source == "mixed":
        warnings.append("This result combines data from different Horizons sources.")
    if terrain_source == "none":
        warnings.append(
            "Terrain masking is not enabled for this site; visibility uses a smooth "
            "0-degree reference horizon."
        )
    else:
        warnings.append(
            "Visibility includes the committed terrain-mask fixture for this site; "
            "replace it with a validated DEM-derived mask for scientific use."
        )
    return AnalysisResponse(
        site=site,
        request=request,
        timeseries=TimeSeries(
            t=times, sun_az=sun_az, sun_el=sun_el, earth_az=earth_az, earth_el=earth_el
        ),
        horizon_mask_deg=horizon_mask,
        sun_intervals=as_intervals(visibility["sun_intervals"]),
        earth_intervals=as_intervals(visibility["earth_intervals"]),
        dark_intervals=as_intervals(visibility["dark_intervals"]),
        metrics=metrics,
        score=score,
        terrain_source=terrain_source,
        data_source=data_source,
        data_quality=data_quality,
        warnings=warnings,
        cached=cached,
    )
