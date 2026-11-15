from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx


class HorizonsError(RuntimeError):
    """Raised when Horizons returns an invalid or unusable response."""


@dataclass(frozen=True)
class EphemerisPoint:
    timestamp: datetime
    azimuth_deg: float
    elevation_deg: float


@dataclass(frozen=True)
class EphemerisSeries:
    points: list[EphemerisPoint]
    cached: bool
    data_source: str
    data_quality: str = "complete"


def _parse_timestamp(value: str) -> datetime:
    value = value.strip().strip('"')
    for fmt in (
        "%Y-%b-%d %H:%M",
        "%Y-%b-%d %H:%M:%S",
        "%Y-%b-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    raise HorizonsError(f"Unsupported Horizons timestamp: {value!r}")


def parse_horizons_response(text: str) -> list[EphemerisPoint]:
    if "API VERSION:" not in text:
        raise HorizonsError("Horizons response is missing API VERSION")
    if "$$SOE" not in text or "$$EOE" not in text:
        raise HorizonsError("Horizons response is missing $$SOE/$$EOE markers")
    if "ERROR" in text.upper() and "$$SOE" not in text:
        raise HorizonsError(text.strip()[-500:])

    block = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    points: list[EphemerisPoint] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        columns = [column.strip() for column in line.split(",")]
        if len(columns) < 3:
            continue
        try:
            timestamp = _parse_timestamp(columns[0])
            numeric = [float(column) for column in columns[1:] if column]
        except ValueError:
            continue
        if len(numeric) < 2:
            continue
        points.append(
            EphemerisPoint(
                timestamp=timestamp,
                azimuth_deg=numeric[-2] % 360,
                elevation_deg=numeric[-1],
            )
        )
    if not points:
        raise HorizonsError("Horizons response contained no parseable ephemeris rows")
    return points


def validate_series(
    points: list[EphemerisPoint],
    *,
    start_utc: datetime,
    duration_days: int,
    step_minutes: int,
) -> None:
    """Reject partial or irregular series before they enter cache or analysis."""
    if not points:
        raise HorizonsError("Horizons response contained no samples")
    if step_minutes <= 0 or duration_days <= 0:
        raise HorizonsError("Horizons series parameters must be positive")
    expected_step = timedelta(minutes=step_minutes)
    expected_count = (duration_days * 24 * 60) // step_minutes
    start = (
        start_utc.replace(tzinfo=timezone.utc)
        if start_utc.tzinfo is None
        else start_utc.astimezone(timezone.utc)
    )
    end = start + timedelta(days=duration_days)
    if points[0].timestamp < start - expected_step or points[0].timestamp > start + expected_step:
        raise HorizonsError("Horizons series starts outside the requested window")
    if len(points) < expected_count:
        raise HorizonsError(
            f"Horizons returned {len(points)} samples; expected at least {expected_count}"
        )
    if points[-1].timestamp < end - expected_step:
        raise HorizonsError("Horizons series does not cover the requested duration")
    for previous, current in zip(points, points[1:]):
        if current.timestamp - previous.timestamp != expected_step:
            raise HorizonsError("Horizons series has irregular timestamp spacing")


class HorizonsClient:
    def __init__(
        self,
        base_url: str,
        cache_dir: str,
        timeout_seconds: float = 20,
        retries: int = 2,
    ) -> None:
        self.base_url = base_url
        self.cache_dir = Path(cache_dir)
        self.timeout_seconds = timeout_seconds
        self.retries = retries

    def _cache_path(self, params: dict[str, str]) -> Path:
        normalized = json.dumps(params, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def fetch(
        self,
        *,
        target: str,
        lon_deg: float,
        lat_deg: float,
        start_utc: datetime,
        duration_days: int,
        step_minutes: int,
    ) -> EphemerisSeries:
        stop_utc = start_utc + timedelta(days=duration_days)
        params = {
            "format": "text",
            "COMMAND": target,
            "CENTER": "coord@301",
            "SITE_COORD": f"{lon_deg:.6f},{lat_deg:.6f},0",
            "COORD_TYPE": "GEODETIC",
            "EPHEM_TYPE": "OBSERVER",
            "QUANTITIES": "4",
            "ANG_FORMAT": "DEG",
            "CAL_FORMAT": "CAL",
            "CSV_FORMAT": "YES",
            "START_TIME": start_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "STOP_TIME": stop_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "STEP_SIZE": f"{step_minutes} m",
        }
        cache_path = self._cache_path(params)
        if cache_path.exists():
            cached_points = self._read_cache(cache_path)
            try:
                validate_series(
                    cached_points,
                    start_utc=start_utc,
                    duration_days=duration_days,
                    step_minutes=step_minutes,
                )
            except HorizonsError:
                cache_path.unlink(missing_ok=True)
            else:
                return EphemerisSeries(
                    points=cached_points,
                    cached=True,
                    data_source="cache",
                )

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = httpx.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                points = parse_horizons_response(response.text)
                validate_series(
                    points,
                    start_utc=start_utc,
                    duration_days=duration_days,
                    step_minutes=step_minutes,
                )
                self._write_cache(cache_path, points)
                return EphemerisSeries(points=points, cached=False, data_source="nasa")
            except (httpx.HTTPError, HorizonsError) as error:
                last_error = error
                if attempt < self.retries:
                    time.sleep(0.25 * (2**attempt))
        raise HorizonsError(f"Horizons request failed: {last_error}")

    @staticmethod
    def _read_cache(path: Path) -> list[EphemerisPoint]:
        payload: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        return [
            EphemerisPoint(
                timestamp=datetime.fromisoformat(item["timestamp"]),
                azimuth_deg=item["azimuth_deg"],
                elevation_deg=item["elevation_deg"],
            )
            for item in payload
        ]

    @staticmethod
    def _write_cache(path: Path, points: list[EphemerisPoint]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "timestamp": point.timestamp.isoformat(),
                "azimuth_deg": point.azimuth_deg,
                "elevation_deg": point.elevation_deg,
            }
            for point in points
        ]
        path.write_text(json.dumps(payload), encoding="utf-8")
