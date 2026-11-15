from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypedDict

from app.backend.integrations.horizons import EphemerisPoint, HorizonsClient, HorizonsError


class FallbackProfile(TypedDict):
    sun_elevation_base_deg: float
    sun_elevation_amplitude_deg: float
    earth_elevation_offset_deg: float
    azimuth_offset_deg: float


_FALLBACK_PROFILES_PATH = Path(__file__).resolve().parents[1] / "data" / "fallback_profiles.json"


def _fallback_profile(site_id: str) -> FallbackProfile:
    profiles = json.loads(_FALLBACK_PROFILES_PATH.read_text(encoding="utf-8"))
    profile = profiles.get(site_id, profiles["custom"])
    return {
        "sun_elevation_base_deg": float(profile["sun_elevation_base_deg"]),
        "sun_elevation_amplitude_deg": float(profile["sun_elevation_amplitude_deg"]),
        "earth_elevation_offset_deg": float(profile["earth_elevation_offset_deg"]),
        "azimuth_offset_deg": float(profile["azimuth_offset_deg"]),
    }


def _build_intervals(
    times: list[datetime],
    visible: list[bool],
    sample_step: timedelta,
    wanted: bool,
) -> list[tuple[datetime, datetime]]:
    intervals: list[tuple[datetime, datetime]] = []
    start: datetime | None = None
    for timestamp, is_visible in zip(times, visible):
        if is_visible == wanted and start is None:
            start = timestamp
        elif is_visible != wanted and start is not None:
            intervals.append((start, timestamp))
            start = None
    if start is not None and times:
        intervals.append((start, times[-1] + sample_step))
    return intervals


def _longest_hours(intervals: list[tuple[datetime, datetime]]) -> float:
    return max(
        ((end - start).total_seconds() / 3600 for start, end in intervals),
        default=0.0,
    )


def calculate_visibility(
    *,
    sun: list[EphemerisPoint],
    earth: list[EphemerisPoint],
    horizon_mask_deg: list[float] | None = None,
    sun_limb_deg: float = 0.0,
) -> dict[str, object]:
    """Calculate smooth-horizon visibility and mission summary metrics."""
    count = min(len(sun), len(earth))
    sun = sun[:count]
    earth = earth[:count]
    if not sun:
        raise ValueError("At least one ephemeris sample is required")
    times = [point.timestamp for point in sun]
    if len(times) > 1:
        sample_step = times[1] - times[0]
    else:
        sample_step = timedelta(minutes=30)
    mask = horizon_mask_deg or [0.0] * 360
    sun_visible = [
        point.elevation_deg + sun_limb_deg > mask[round(point.azimuth_deg) % 360]
        for point in sun
    ]
    earth_visible = [
        point.elevation_deg > mask[round(point.azimuth_deg) % 360]
        for point in earth
    ]
    sun_intervals = _build_intervals(times, sun_visible, sample_step, True)
    dark_intervals = _build_intervals(times, sun_visible, sample_step, False)
    earth_intervals = _build_intervals(times, earth_visible, sample_step, True)
    comm_outages = _build_intervals(times, earth_visible, sample_step, False)
    mission_hours = len(times) * sample_step.total_seconds() / 3600
    lit_elevations = [
        point.elevation_deg for point, visible in zip(sun, sun_visible) if visible
    ]
    first_sunset = next(
        (timestamp for timestamp, visible in zip(times, sun_visible) if not visible),
        None,
    )
    first_earthset = next(
        (timestamp for timestamp, visible in zip(times, earth_visible) if not visible),
        None,
    )
    time_to_sunset = (
        0.0
        if not sun_visible[0]
        else (
            (first_sunset - times[0]).total_seconds() / 3600
            if first_sunset
            else None
        )
    )
    time_to_earthset = (
        0.0
        if not earth_visible[0]
        else (
            (first_earthset - times[0]).total_seconds() / 3600
            if first_earthset
            else None
        )
    )
    illumination_pct = sum(sun_visible) / count * 100
    comm_pct = sum(earth_visible) / count * 100
    overlap_pct = (
        sum(a and b for a, b in zip(sun_visible, earth_visible)) / count * 100
    )
    longest_dark = _longest_hours(dark_intervals)
    longest_comm_outage = _longest_hours(comm_outages)
    survivability = max(
        0.0,
        100.0 - (longest_dark / mission_hours * 100 if mission_hours else 100.0),
    )
    score = {
        "power": illumination_pct,
        "communication": comm_pct,
        "survivability": survivability,
        "total": illumination_pct * 0.4 + comm_pct * 0.3 + survivability * 0.3,
    }
    return {
        "times": times,
        "sun_visible": sun_visible,
        "earth_visible": earth_visible,
        "sun_intervals": sun_intervals,
        "earth_intervals": earth_intervals,
        "dark_intervals": dark_intervals,
        "comm_outages": comm_outages,
        "metrics": {
            "illumination_pct": illumination_pct,
            "comm_pct": comm_pct,
            "sun_elevation_max_deg": max(point.elevation_deg for point in sun),
            "sun_elevation_mean_deg": (
                sum(lit_elevations) / len(lit_elevations) if lit_elevations else 0.0
            ),
            "longest_dark_hours": longest_dark,
            "longest_comm_outage_hours": longest_comm_outage,
            "n_dark_periods": len(dark_intervals),
            "n_comm_outages": len(comm_outages),
            "time_to_sunset_hours": time_to_sunset,
            "time_to_earthset_hours": time_to_earthset,
            "overlap_pct": overlap_pct,
        },
        "score": score,
    }


def fallback_series(
    start_utc: datetime,
    duration_days: int,
    step_minutes: int,
    profile: FallbackProfile,
) -> tuple[list[datetime], list[float], list[float]]:
    count = max(1, (duration_days * 24 * 60) // step_minutes)
    times = [start_utc + timedelta(minutes=index * step_minutes) for index in range(count)]
    azimuth = [
        (profile["azimuth_offset_deg"] + index * 360 / count) % 360
        for index in range(count)
    ]
    cycle = max(2, round(24 * 60 / step_minutes))
    elevation = [
        profile["sun_elevation_base_deg"]
        + profile["sun_elevation_amplitude_deg"]
        * math.sin(2 * math.pi * index / cycle)
        for index in range(count)
    ]
    return times, azimuth, elevation


def get_sun_earth_series(
    client: HorizonsClient,
    *,
    lat_deg: float,
    lon_deg: float,
    site_id: str = "custom",
    start_utc: datetime,
    duration_days: int,
    step_minutes: int,
) -> tuple[list[EphemerisPoint], list[EphemerisPoint], bool, str, str]:
    try:
        sun = client.fetch(
            target="10",
            lon_deg=lon_deg,
            lat_deg=lat_deg,
            start_utc=start_utc,
            duration_days=duration_days,
            step_minutes=step_minutes,
        )
        earth = client.fetch(
            target="399",
            lon_deg=lon_deg,
            lat_deg=lat_deg,
            start_utc=start_utc,
            duration_days=duration_days,
            step_minutes=step_minutes,
        )
        if sun.data_source == earth.data_source:
            data_source = sun.data_source
        else:
            data_source = "mixed"
        return (
            sun.points,
            earth.points,
            sun.cached and earth.cached,
            data_source,
            "complete",
        )
    except HorizonsError:
        profile = _fallback_profile(site_id)
        times, sun_az, sun_el = fallback_series(
            start_utc, duration_days, step_minutes, profile
        )
        _, earth_az, earth_el = fallback_series(
            start_utc + timedelta(minutes=15),
            duration_days,
            step_minutes,
            profile,
        )
        sun_points = [
            EphemerisPoint(t, az, el) for t, az, el in zip(times, sun_az, sun_el)
        ]
        earth_points = [
            EphemerisPoint(
                t,
                (az + 180) % 360,
                el + profile["earth_elevation_offset_deg"],
            )
            for t, az, el in zip(times, earth_az, earth_el)
        ]
        return sun_points, earth_points, False, "fallback", "fallback"
