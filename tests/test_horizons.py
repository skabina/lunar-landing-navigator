from datetime import datetime, timedelta, timezone

from app.backend.integrations.horizons import (
    HorizonsClient,
    HorizonsError,
    parse_horizons_response,
    validate_series,
)


def test_parse_horizons_csv_response() -> None:
    response = """API VERSION: 1.0
$$SOE
2026-Jan-01 00:00:00.000, 12.5, 3.25
2026-Jan-01 00:30, 180.0, -2.0
$$EOE
"""
    points = parse_horizons_response(response)
    assert len(points) == 2
    assert points[0].timestamp.tzinfo == timezone.utc
    assert points[0].azimuth_deg == 12.5
    assert points[1].elevation_deg == -2.0


def test_horizons_client_reuses_disk_cache(monkeypatch, tmp_path) -> None:
    rows = []
    for index in range(48):
        timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(
            minutes=index * 30
        )
        rows.append(f"{timestamp.strftime('%Y-%b-%d %H:%M')}, 12.5, 3.25")

    class MockResponse:
        text = "API VERSION: 1.0\n$$SOE\n" + "\n".join(rows) + "\n$$EOE\n"

        def raise_for_status(self) -> None:
            return None

    calls = 0

    def fake_get(*args, **kwargs):
        nonlocal calls
        calls += 1
        return MockResponse()

    monkeypatch.setattr("httpx.get", fake_get)
    client = HorizonsClient("https://example.test", str(tmp_path))
    kwargs = {
        "target": "10",
        "lon_deg": 0,
        "lat_deg": -89.9,
        "start_utc": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "duration_days": 1,
        "step_minutes": 30,
    }
    first = client.fetch(**kwargs)
    second = client.fetch(**kwargs)
    assert first.data_source == "nasa"
    assert second.data_source == "cache"
    assert calls == 1


def test_validate_series_rejects_partial_response() -> None:
    points = parse_horizons_response(
        """API VERSION: 1.0
$$SOE
2026-Jan-01 00:00, 10, 2
2026-Jan-01 00:30, 20, 3
$$EOE
"""
    )
    try:
        validate_series(
            points,
            start_utc=points[0].timestamp,
            duration_days=1,
            step_minutes=30,
        )
    except HorizonsError as error:
        assert "expected at least" in str(error)
    else:
        raise AssertionError("partial series should be rejected")
