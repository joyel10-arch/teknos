"""
zone_engine.py — Zone config loading, validation, and membership testing.

WHAT: Loads zone JSON templates (Section 7.1), validates them with Pydantic,
      scales polygons to the actual video resolution, and provides per-frame
      zone membership testing with hysteresis to prevent boundary flicker.

WHY hysteresis?  A person walking near a zone boundary will have their
bottom-centre point oscillate in and out of the zone due to bounding-box jitter
and tracking noise.  Without hysteresis this creates phantom entries and exits
every few frames.  We require ZONE_MIN_FRAMES consecutive frames agreeing before
the membership state changes (a simple state machine per track per zone).

Zone priority: when a person is in overlapping zones, the zone with the highest
*priority* value is used as the "display zone" label.  All zones the person is
in are recorded in current_zones (a list).  Priority does NOT affect event
generation — events are fired for every zone the person is in.

Directional zones: allowed_direction must be one of the four axis-aligned
directions.  The behaviour engine checks the direction; this module only handles
membership and loading.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.geometry import point_in_polygon, scale_polygon

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic zone models (validation on load)
# ─────────────────────────────────────────────────────────────────────────────

ZoneType = Literal["allowed", "monitored", "restricted", "directional"]
DirectionType = Literal[
    "left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"
]


class ZoneConfig(BaseModel):
    """One zone polygon definition."""
    id: str
    name: str
    type: ZoneType
    priority: int = Field(default=1, ge=1)
    polygon: list[list[float]] = Field(min_length=3)
    allowed_direction: DirectionType | None = None

    @field_validator("polygon")
    @classmethod
    def polygon_has_three_points(cls, v: list) -> list:
        if len(v) < 3:
            raise ValueError("polygon must have at least 3 points")
        for pt in v:
            if len(pt) != 2:
                raise ValueError(f"each polygon point must be [x, y], got {pt}")
        return v

    @model_validator(mode="after")
    def directional_needs_direction(self) -> "ZoneConfig":
        if self.type == "directional" and self.allowed_direction is None:
            raise ValueError(
                f"Zone '{self.id}' (type=directional) must have allowed_direction"
            )
        return self


class SceneConfig(BaseModel):
    """Top-level scene (zone template) configuration."""
    scene_id: str
    scene_name: str
    video_name: str
    reference_resolution: list[int] = Field(min_length=2, max_length=2)
    params: dict[str, Any] = Field(default_factory=dict)
    zones: list[ZoneConfig]

    @field_validator("zones")
    @classmethod
    def unique_zone_ids(cls, v: list) -> list:
        ids = [z.id for z in v]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Zone ids must be unique; got duplicates in {ids}")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Runtime zone engine
# ─────────────────────────────────────────────────────────────────────────────

class ZoneEngine:
    """Manages zones for one analysis run.

    Usage:
        engine = ZoneEngine.from_file(path, actual_width, actual_height)
        membership = engine.get_memberships([px, py])      # -> list[str]  zone ids
        engine.update_hysteresis(track_id, membership)     # update state machine
        stable_membership = engine.get_stable_zones(track_id)
    """

    def __init__(
        self,
        scene: SceneConfig,
        actual_width: int,
        actual_height: int,
        zone_min_frames: int = 3,
    ) -> None:
        self.scene = scene
        self.actual_width = actual_width
        self.actual_height = actual_height
        self.zone_min_frames = zone_min_frames

        ref_w, ref_h = scene.reference_resolution

        # Scale polygons to actual resolution
        self._zones: list[ZoneConfig] = []
        self._scaled_polygons: dict[str, list[list[float]]] = {}

        for z in scene.zones:
            scaled = scale_polygon(
                z.polygon, ref_w, ref_h, actual_width, actual_height
            )
            self._scaled_polygons[z.id] = scaled
            self._zones.append(z)

        # Sort by priority descending for "display zone" selection
        self._zones_by_priority = sorted(
            self._zones, key=lambda z: z.priority, reverse=True
        )

        # Hysteresis state machine: track_id -> {zone_id -> (inside: bool, consecutive: int)}
        # 'consecutive' counts how many frames in a row the RAW membership equals 'candidate'
        # 'inside' is the confirmed (hysteresis-stable) state
        self._hysteresis: dict[int, dict[str, dict]] = {}

    @classmethod
    def from_file(
        cls,
        path: Path | str,
        actual_width: int,
        actual_height: int,
        zone_min_frames: int = 3,
    ) -> "ZoneEngine":
        """Load and validate a scene config JSON, return a ZoneEngine."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Zone config not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        scene = SceneConfig.model_validate(raw)
        logger.info(
            "Loaded scene '%s' with %d zones from %s",
            scene.scene_id, len(scene.zones), path,
        )
        return cls(scene, actual_width, actual_height, zone_min_frames)

    def get_zone_by_id(self, zone_id: str) -> ZoneConfig | None:
        """Return the ZoneConfig for a given zone id."""
        return next((z for z in self._zones if z.id == zone_id), None)

    def raw_memberships(self, point: list[float]) -> list[str]:
        """Return list of zone ids whose polygon contains *point* (no hysteresis).

        *point* must be in actual-resolution coordinates.
        """
        return [
            z.id for z in self._zones
            if point_in_polygon(point, self._scaled_polygons[z.id])
        ]

    def update_hysteresis(self, track_id: int, raw_zones: list[str]) -> None:
        """Advance the hysteresis state machine for *track_id* given *raw_zones*.

        Must be called once per frame, in frame order.
        After calling this, use get_stable_zones() to read the confirmed state.
        """
        if track_id not in self._hysteresis:
            self._hysteresis[track_id] = {
                z.id: {"stable": False, "candidate": False, "count": 0}
                for z in self._zones
            }

        state = self._hysteresis[track_id]
        raw_set = set(raw_zones)

        for zone_id, s in state.items():
            raw_inside = zone_id in raw_set
            if raw_inside == s["candidate"]:
                # Same as last frame: increment consecutive counter
                s["count"] += 1
            else:
                # Changed: reset counter, update candidate
                s["candidate"] = raw_inside
                s["count"] = 1

            # Confirm state change after ZONE_MIN_FRAMES consecutive agreement
            if s["count"] >= self.zone_min_frames:
                s["stable"] = s["candidate"]

    def get_stable_zones(self, track_id: int) -> list[str]:
        """Return the hysteresis-confirmed zone ids for *track_id*."""
        state = self._hysteresis.get(track_id, {})
        return [zid for zid, s in state.items() if s["stable"]]

    def get_display_zone(self, track_id: int) -> str | None:
        """Return the highest-priority stable zone id, or None if not in any."""
        stable = set(self.get_stable_zones(track_id))
        for z in self._zones_by_priority:
            if z.id in stable:
                return z.id
        return None

    def scaled_polygon(self, zone_id: str) -> list[list[float]]:
        """Return the scaled polygon for *zone_id* (for rendering)."""
        return self._scaled_polygons.get(zone_id, [])

    def all_zones(self) -> list[ZoneConfig]:
        """Return all zone definitions."""
        return self._zones
