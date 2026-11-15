import json

import pytest

from app.backend.integrations import terrain


def test_missing_terrain_mask_uses_smooth_horizon() -> None:
    mask, source = terrain.load_horizon_mask("missing-site")

    assert source == "none"
    assert mask == [0.0] * 360


def test_terrain_mask_fixture_is_validated(monkeypatch, tmp_path) -> None:
    terrain_dir = tmp_path / "terrain_masks"
    terrain_dir.mkdir()
    (terrain_dir / "demo.json").write_text(json.dumps([2.5] * 360), encoding="utf-8")
    monkeypatch.setattr(terrain, "_TERRAIN_DIR", terrain_dir)

    mask, source = terrain.load_horizon_mask("demo")

    assert source == "fixture"
    assert len(mask) == 360
    assert mask[0] == 2.5


def test_invalid_terrain_mask_fixture_is_rejected(monkeypatch, tmp_path) -> None:
    terrain_dir = tmp_path / "terrain_masks"
    terrain_dir.mkdir()
    (terrain_dir / "broken.json").write_text(json.dumps([1.0]), encoding="utf-8")
    monkeypatch.setattr(terrain, "_TERRAIN_DIR", terrain_dir)

    with pytest.raises(ValueError, match="exactly 360"):
        terrain.load_horizon_mask("broken")
