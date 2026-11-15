from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app


def horizons_text(first_elevation: float, second_elevation: float) -> str:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(48):
        elevation = (
            first_elevation
            if index == 0
            else second_elevation
            if index == 1
            else second_elevation
        )
        timestamp = start + timedelta(minutes=index * 30)
        rows.append(
            f"{timestamp.strftime('%Y-%b-%d %H:%M')}, {10 + index}, {elevation}"
        )
    return "API VERSION: 1.0\n$$SOE\n" + "\n".join(rows) + "\n$$EOE\n"


def test_analyze_uses_offline_fallback(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("HORIZONS_URL", "http://127.0.0.1:1/unavailable")
    from app.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.post(
        "/api/v1/analyze-site",
        json={"site_id": "shackleton-rim", "start_utc": "2026-01-01T00:00:00Z"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_source"] == "fallback"
    assert payload["data_quality"] == "fallback"
    assert any("fallback" in warning.lower() for warning in payload["warnings"])
    assert len(payload["timeseries"]["t"]) > 0


def test_fallback_profile_differs_by_site(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("HORIZONS_URL", "http://127.0.0.1:1/unavailable")
    from app.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    payloads = [
        client.post(
            "/api/v1/analyze-site",
            json={
                "site_id": site_id,
                "start_utc": "2026-01-01T00:00:00Z",
                "duration_days": 1,
            },
        ).json()
        for site_id in ("shackleton-rim", "apollo-11")
    ]
    assert payloads[0]["data_source"] == payloads[1]["data_source"] == "fallback"
    assert payloads[0]["timeseries"]["sun_el"] != payloads[1]["timeseries"]["sun_el"]


def test_analyze_uses_mocked_nasa_response(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("HORIZONS_URL", "https://example.test/horizons")
    from app.config import get_settings

    get_settings.cache_clear()

    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        text = horizons_text(4.0, 5.0)

    def fake_get(url, *, params, timeout):
        assert url == "https://example.test/horizons"
        assert params["CENTER"] == "coord@301"
        return MockResponse()

    monkeypatch.setattr("httpx.get", fake_get)
    client = TestClient(app)
    response = client.post(
        "/api/v1/analyze-site",
        json={
            "site_id": "shackleton-rim",
            "start_utc": "2026-01-01T00:00:00Z",
            "duration_days": 1,
            "step_minutes": 30,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_source"] == "nasa"
    assert payload["data_quality"] == "complete"
    assert any("terrain" in warning.lower() for warning in payload["warnings"])
    assert payload["timeseries"]["sun_az"][:2] == [10.0, 11.0]
    assert len(payload["timeseries"]["sun_az"]) == 48
    assert payload["metrics"]["illumination_pct"] == 100


def test_analyze_negative_sun_elevation_is_not_fully_lit(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("HORIZONS_URL", "https://example.test/horizons")
    from app.config import get_settings

    get_settings.cache_clear()

    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        text = horizons_text(-4.0, -2.0)

    monkeypatch.setattr("httpx.get", lambda *args, **kwargs: MockResponse())
    response = TestClient(app).post(
        "/api/v1/analyze-site",
        json={
            "site_id": "shackleton-rim",
            "start_utc": "2026-01-01T00:00:00Z",
            "duration_days": 1,
            "step_minutes": 30,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["illumination_pct"] == 0
    assert payload["score"]["power"] == 0


def test_compare_summary_is_not_mock(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("HORIZONS_URL", "https://example.test/horizons")
    from app.config import get_settings

    get_settings.cache_clear()

    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        text = horizons_text(-2.0, 4.0)

    monkeypatch.setattr("httpx.get", lambda *args, **kwargs: MockResponse())
    response = TestClient(app).post(
        "/api/v1/compare",
        json={
            "scenarios": [
                {
                    "site_id": "shackleton-rim",
                    "start_utc": "2026-01-01T00:00:00Z",
                    "duration_days": 1,
                },
                {
                    "site_id": "malapert-massif",
                    "start_utc": "2026-01-01T00:00:00Z",
                    "duration_days": 1,
                },
            ]
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "mock scenarios" not in payload["summary"].lower()
    assert "sources:" in payload["summary"]
