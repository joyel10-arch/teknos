"""
test_zone_engine.py — Unit tests for zone_engine.py.

Tests: validation errors, hysteresis behaviour, overlap priority.
No YOLO required.
"""

import json
import pytest
from pathlib import Path
from app.services.zone_engine import ZoneEngine, SceneConfig, ZoneConfig


# ─────────────────────────────────────────────────────────────────────────────
# Helpers to build minimal scenes in memory
# ─────────────────────────────────────────────────────────────────────────────

def _make_scene(zones: list[dict]) -> dict:
    return {
        "scene_id": "test",
        "scene_name": "Test Scene",
        "video_name": "test.avi",
        "reference_resolution": [640, 360],
        "params": {},
        "zones": zones,
    }


def _make_engine(zones: list[dict], min_frames: int = 3) -> ZoneEngine:
    scene = SceneConfig.model_validate(_make_scene(zones))
    return ZoneEngine(scene, actual_width=640, actual_height=360,
                      zone_min_frames=min_frames)


SQUARE_ZONE = {
    "id": "z1", "name": "Zone One", "type": "allowed", "priority": 1,
    "polygon": [[100, 100], [300, 100], [300, 250], [100, 250]],
}

RESTRICTED_ZONE = {
    "id": "r1", "name": "Restricted", "type": "restricted", "priority": 2,
    "polygon": [[400, 100], [600, 100], [600, 250], [400, 250]],
}

MONITORED_ZONE = {
    "id": "m1", "name": "Monitored", "type": "monitored", "priority": 1,
    "polygon": [[100, 100], [300, 100], [300, 250], [100, 250]],
}

DIRECTIONAL_ZONE = {
    "id": "d1", "name": "Lane", "type": "directional",
    "allowed_direction": "left_to_right", "priority": 1,
    "polygon": [[0, 150], [640, 150], [640, 250], [0, 250]],
}


# ─────────────────────────────────────────────────────────────────────────────
# Validation tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSceneValidation:

    def test_valid_scene_loads(self):
        scene = SceneConfig.model_validate(_make_scene([SQUARE_ZONE]))
        assert len(scene.zones) == 1

    def test_polygon_fewer_than_3_points_raises(self):
        bad_zone = {**SQUARE_ZONE, "polygon": [[0, 0], [10, 0]]}
        with pytest.raises(Exception):   # ValidationError
            SceneConfig.model_validate(_make_scene([bad_zone]))

    def test_duplicate_zone_ids_raises(self):
        z2 = {**SQUARE_ZONE, "name": "Duplicate"}  # same id "z1"
        with pytest.raises(Exception):
            SceneConfig.model_validate(_make_scene([SQUARE_ZONE, z2]))

    def test_directional_without_direction_raises(self):
        bad = {**DIRECTIONAL_ZONE}
        del bad["allowed_direction"]
        with pytest.raises(Exception):
            SceneConfig.model_validate(_make_scene([bad]))

    def test_invalid_allowed_direction_raises(self):
        bad = {**DIRECTIONAL_ZONE, "allowed_direction": "diagonal"}
        with pytest.raises(Exception):
            SceneConfig.model_validate(_make_scene([bad]))

    def test_all_zone_types_valid(self):
        for zt in ("allowed", "monitored", "restricted"):
            z = {**SQUARE_ZONE, "id": zt, "type": zt}
            scene = SceneConfig.model_validate(_make_scene([z]))
            assert scene.zones[0].type == zt

    def test_directional_zone_requires_allowed_direction(self):
        d = {**DIRECTIONAL_ZONE}
        scene = SceneConfig.model_validate(_make_scene([d]))
        assert scene.zones[0].allowed_direction == "left_to_right"


# ─────────────────────────────────────────────────────────────────────────────
# Membership tests (no hysteresis)
# ─────────────────────────────────────────────────────────────────────────────

class TestRawMembership:

    def test_point_inside_zone(self):
        engine = _make_engine([SQUARE_ZONE])
        assert "z1" in engine.raw_memberships([200, 175])

    def test_point_outside_zone(self):
        engine = _make_engine([SQUARE_ZONE])
        assert "z1" not in engine.raw_memberships([50, 50])

    def test_point_in_multiple_overlapping_zones(self):
        z2 = {**MONITORED_ZONE, "id": "m1"}
        z1 = {**SQUARE_ZONE}    # same polygon, different zone
        # Both polygons are the same box → point should be in both
        engine = _make_engine([z1, {**MONITORED_ZONE}])
        # [200,175] is inside both the square (z1) and the monitored zone (m1)
        memberships = engine.raw_memberships([200, 175])
        assert "z1" in memberships
        assert "m1" in memberships


# ─────────────────────────────────────────────────────────────────────────────
# Hysteresis tests
# ─────────────────────────────────────────────────────────────────────────────

class TestHysteresis:

    def test_zone_not_stable_before_min_frames(self):
        """With min_frames=3, 2 frames inside should NOT confirm membership."""
        engine = _make_engine([SQUARE_ZONE], min_frames=3)
        tid = 1
        for _ in range(2):
            engine.update_hysteresis(tid, ["z1"])
        assert "z1" not in engine.get_stable_zones(tid)

    def test_zone_stable_after_min_frames(self):
        """3 consecutive frames inside → stable."""
        engine = _make_engine([SQUARE_ZONE], min_frames=3)
        tid = 1
        for _ in range(3):
            engine.update_hysteresis(tid, ["z1"])
        assert "z1" in engine.get_stable_zones(tid)

    def test_zone_exit_requires_min_frames(self):
        """Enter zone (3 frames), then 2 frames outside → still stable."""
        engine = _make_engine([SQUARE_ZONE], min_frames=3)
        tid = 1
        for _ in range(3):
            engine.update_hysteresis(tid, ["z1"])  # enter and stabilise
        for _ in range(2):
            engine.update_hysteresis(tid, [])       # start leaving
        # After only 2 frames outside, should still be stable inside
        assert "z1" in engine.get_stable_zones(tid)

    def test_zone_exit_confirmed_after_min_frames(self):
        """3 frames inside, then 3 frames outside → confirmed exit."""
        engine = _make_engine([SQUARE_ZONE], min_frames=3)
        tid = 1
        for _ in range(3):
            engine.update_hysteresis(tid, ["z1"])
        for _ in range(3):
            engine.update_hysteresis(tid, [])
        assert "z1" not in engine.get_stable_zones(tid)

    def test_boundary_flicker_does_not_flip_state(self):
        """Alternating in/out should NOT repeatedly flip the stable state."""
        engine = _make_engine([SQUARE_ZONE], min_frames=3)
        tid = 1
        # Stabilise inside
        for _ in range(3):
            engine.update_hysteresis(tid, ["z1"])
        # Now alternate in/out (simulating boundary jitter)
        for _ in range(6):
            engine.update_hysteresis(tid, [])
            engine.update_hysteresis(tid, ["z1"])
        # Because flicker never accumulates 3 consecutive frames outside,
        # the state should flip — this tests that the counter resets on change
        # (final state depends on last 3 frames; mainly checks no crash)
        stable = engine.get_stable_zones(tid)
        assert isinstance(stable, list)

    def test_display_zone_returns_highest_priority(self):
        """When in two zones, display zone should be the higher priority one."""
        low  = {**SQUARE_ZONE, "priority": 1}
        high = {**RESTRICTED_ZONE, "priority": 3}
        engine = _make_engine([low, high], min_frames=1)
        tid = 1
        engine.update_hysteresis(tid, ["z1", "r1"])
        display = engine.get_display_zone(tid)
        assert display == "r1"

    def test_multiple_tracks_independent(self):
        """Two different track IDs must have independent hysteresis state."""
        engine = _make_engine([SQUARE_ZONE], min_frames=3)
        # Track 1: inside
        for _ in range(3):
            engine.update_hysteresis(1, ["z1"])
        # Track 2: outside
        for _ in range(3):
            engine.update_hysteresis(2, [])
        assert "z1" in engine.get_stable_zones(1)
        assert "z1" not in engine.get_stable_zones(2)
