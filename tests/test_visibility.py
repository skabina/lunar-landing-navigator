from datetime import datetime, timedelta, timezone

from app.backend.integrations.horizons import EphemerisPoint
from app.backend.services.analysis_service import calculate_visibility


def points(elevations: list[float]) -> list[EphemerisPoint]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        EphemerisPoint(
            timestamp=start + timedelta(hours=index),
            azimuth_deg=0,
            elevation_deg=elevation,
        )
        for index, elevation in enumerate(elevations)
    ]


def test_visibility_builds_intervals_and_metrics() -> None:
    result = calculate_visibility(
        sun=points([5, 2, -1, -3]),
        earth=points([3, -1, -2, 4]),
    )

    assert result["metrics"]["illumination_pct"] == 50
    assert result["metrics"]["comm_pct"] == 50
    assert result["metrics"]["longest_dark_hours"] == 2
    assert result["metrics"]["longest_comm_outage_hours"] == 2
    assert result["metrics"]["time_to_sunset_hours"] == 2
    assert result["metrics"]["time_to_earthset_hours"] == 1
    assert result["metrics"]["overlap_pct"] == 25
    assert result["score"]["total"] < 100


def test_visibility_applies_azimuth_indexed_horizon_mask() -> None:
    result = calculate_visibility(
        sun=[
            EphemerisPoint(
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                azimuth_deg=10,
                elevation_deg=3,
            )
        ],
        earth=[
            EphemerisPoint(
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                azimuth_deg=10,
                elevation_deg=3,
            )
        ],
        horizon_mask_deg=[0.0] * 10 + [5.0] + [0.0] * 349,
    )

    assert result["metrics"]["illumination_pct"] == 0
    assert result["metrics"]["comm_pct"] == 0
