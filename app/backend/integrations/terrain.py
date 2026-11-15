from __future__ import annotations

import json
from pathlib import Path


_TERRAIN_DIR = Path(__file__).resolve().parents[1] / "data" / "terrain_masks"


def load_horizon_mask(site_id: str) -> tuple[list[float], str]:
    """Load a validated 360-degree terrain mask when a site fixture exists."""
    path = _TERRAIN_DIR / f"{site_id}.json"
    if not path.exists():
        return [0.0] * 360, "none"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) != 360:
        raise ValueError(f"Terrain mask must contain exactly 360 values: {path.name}")
    mask = [float(value) for value in payload]
    return mask, "fixture"
