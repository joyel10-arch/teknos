"""
behaviour_engine.py — Per-track rule-based event detection (Stage 2c).

WHAT: Takes processed tracks (with zone membership) and fires rule-based events.
      This is NOT a trained action-recognition model — it is "trajectory-based
      behavioural state recognition": rules operating on smoothed position, speed,
      dwell time, and zone membership over time.

Rules implemented (see Section 8 of the master prompt):
  Rule 1 — normal_walkthrough (info):   steady movement through an allowed zone
  Rule 2 — restricted_zone_entry (high): first frame inside a restricted zone
  Rule 3 — loitering (medium):           long low-movement dwell in monitored zone
  Rule 4 — wrong_direction_movement (medium): reverse travel in directional zone

Pixel-threshold scaling:
  All thresholds are defined at REFERENCE_HEIGHT=360, REFERENCE_WIDTH=640 and
  multiplied by (frame_height / 360) or (frame_width / 640) at runtime.
  This is documented in config.py and referenced here via the scale factors
  passed to run_behaviour_engine().

Known limitation: rules only fire on is_valid_track=True tracks.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.services.track_processor import TrackData, FrameRecord
from app.services.zone_engine import ZoneEngine, ZoneConfig

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Event model (mirrors Section 7.3)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BehaviourEvent:
    """One detected behavioural event."""
    event_id: str
    video_id: str
    entity_id: str
    track_id: int
    event_type: str   # restricted_zone_entry | loitering | wrong_direction_movement | normal_walkthrough
    severity: str     # info | medium | high
    start_time_seconds: float
    end_time_seconds: float
    duration_seconds: float | None
    zone_id: str
    zone_name: str
    confidence: float              # Evidence Confidence (computed later by confidence.py)
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)
    evidence_frame_path: str = ""
    # Raw components for confidence.py
    _det_confidences: list[float] = field(default_factory=list, repr=False)
    _observed_frames: int = 0
    _expected_frames: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def run_behaviour_engine(
    tracks: list[TrackData],
    zone_engine: ZoneEngine,
    video_id: str,
    fps: float,
    frame_width: int,
    frame_height: int,
    # Rule thresholds (all have defaults matching config.py)
    min_walk_seconds: float = 1.5,
    restricted_reentry_cooldown: float = 2.0,
    count_initial_inside_as_entry: bool = False,
    loitering_duration_seconds: float = 10.0,
    movement_window_seconds: float = 3.0,
    max_avg_speed_px_s: float = 8.0,
    min_direction_travel_px: float = 80.0,
    ref_height: int = 360,
    ref_width: int = 640,
) -> list[BehaviourEvent]:
    """Run all four rules over every valid track.  Return list of events.

    Parameters
    ----------
    tracks       : processed tracks (from track_processor)
    zone_engine  : loaded zone engine (zones already scaled to video resolution)
    video_id     : identifier for the video (used in event_id generation)
    fps          : video frame rate
    frame_width / frame_height : actual video resolution (for pixel scaling)
    All other parameters : rule thresholds (see config.py for documentation)
    """
    # ── Pixel scale factors (thresholds defined at 640×360 reference) ────────
    scale_y = frame_height / ref_height   # for speed and y-distances
    scale_x = frame_width  / ref_width    # for x-distances (directional travel)

    # Apply scaling to pixel thresholds
    max_speed_scaled  = max_avg_speed_px_s   * scale_y
    min_travel_scaled = min_direction_travel_px * scale_x

    events: list[BehaviourEvent] = []
    event_counter = 0  # sequential per video, ordered by start time

    # Only process valid tracks — short/invalid tracks NEVER generate events
    valid_tracks = [t for t in tracks if t.is_valid_track]
    logger.info(
        "Behaviour engine: %d valid tracks, %d total", len(valid_tracks), len(tracks)
    )

    for track in valid_tracks:
        frames = track.frames
        if not frames:
            continue

        new_events = _process_track(
            track=track,
            frames=frames,
            zone_engine=zone_engine,
            video_id=video_id,
            fps=fps,
            min_walk_seconds=min_walk_seconds,
            restricted_reentry_cooldown=restricted_reentry_cooldown,
            count_initial_inside_as_entry=count_initial_inside_as_entry,
            loitering_duration_seconds=loitering_duration_seconds,
            movement_window_seconds=movement_window_seconds,
            max_speed_scaled=max_speed_scaled,
            min_travel_scaled=min_travel_scaled,
            scale_x=scale_x,
            scale_y=scale_y,
        )
        events.extend(new_events)

    # ── Assign sequential event IDs ordered by start time ────────────────────
    events.sort(key=lambda e: e.start_time_seconds)
    for i, evt in enumerate(events, start=1):
        evt.event_id = f"evt_{i:03d}"

    unusual = [e for e in events if e.severity != "info"]
    logger.info(
        "Events generated: %d total, %d unusual (medium/high)",
        len(events), len(unusual),
    )
    return events


# ─────────────────────────────────────────────────────────────────────────────
# Per-track processing
# ─────────────────────────────────────────────────────────────────────────────

def _process_track(
    track: TrackData,
    frames: list[FrameRecord],
    zone_engine: ZoneEngine,
    video_id: str,
    fps: float,
    min_walk_seconds: float,
    restricted_reentry_cooldown: float,
    count_initial_inside_as_entry: bool,
    loitering_duration_seconds: float,
    movement_window_seconds: float,
    max_speed_scaled: float,
    min_travel_scaled: float,
    scale_x: float,
    scale_y: float,
) -> list[BehaviourEvent]:
    """Run all rules for a single track.  Returns events generated."""
    events: list[BehaviourEvent] = []

    # Build hysteresis-stable zone membership per frame
    # (zone_engine must have been fed update_hysteresis per frame already,
    #  OR we do it here for offline analysis)
    # For offline batch analysis, we feed all frames through hysteresis now:
    for fr in frames:
        raw_zones = zone_engine.raw_memberships(fr.bottom_center)
        zone_engine.update_hysteresis(track.track_id, raw_zones)
        # Store stable zones on the frame record
        fr_stable = zone_engine.get_stable_zones(track.track_id)
        # We attach it as an attribute for downstream rules
        fr._stable_zones = fr_stable  # type: ignore[attr-defined]

    # ── Rule 2: restricted zone entry ──────────────────────────────────────
    events.extend(_rule_restricted_entry(
        track, frames, zone_engine, video_id, fps,
        restricted_reentry_cooldown, count_initial_inside_as_entry,
    ))

    # ── Rule 3: loitering ─────────────────────────────────────────────────
    events.extend(_rule_loitering(
        track, frames, zone_engine, video_id, fps,
        loitering_duration_seconds, movement_window_seconds, max_speed_scaled,
    ))

    # ── Rule 4: wrong direction movement ──────────────────────────────────
    events.extend(_rule_wrong_direction(
        track, frames, zone_engine, video_id, fps, min_travel_scaled,
    ))

    # ── Rule 1: normal walkthrough (fires only if no other events on track) ─
    events.extend(_rule_walkthrough(
        track, frames, zone_engine, video_id, fps, min_walk_seconds,
        existing_events=events,
    ))

    return events


# ─────────────────────────────────────────────────────────────────────────────
# Rule implementations
# ─────────────────────────────────────────────────────────────────────────────

def _rule_restricted_entry(
    track: TrackData,
    frames: list[FrameRecord],
    zone_engine: ZoneEngine,
    video_id: str,
    fps: float,
    cooldown_seconds: float,
    count_initial_inside_as_entry: bool,
) -> list[BehaviourEvent]:
    """Rule 2: fire once per entry into a restricted zone."""
    events: list[BehaviourEvent] = []
    restricted_zones = [z for z in zone_engine.all_zones() if z.type == "restricted"]

    for zone in restricted_zones:
        last_inside = False
        last_entry_time: float | None = None
        is_first_valid_frame = True

        for fr in frames:
            stable = getattr(fr, "_stable_zones", [])
            currently_inside = zone.id in stable

            if is_first_valid_frame and not fr.is_interpolated:
                if currently_inside and not count_initial_inside_as_entry:
                    # Person was already inside at first observed frame.
                    # Do not fire an entry event (documented limitation).
                    last_inside = True
                    is_first_valid_frame = False
                    continue
                is_first_valid_frame = False

            if currently_inside and not last_inside:
                # Transition: outside -> inside (entry detected)
                # Check cooldown: do not re-fire within cooldown_seconds of last entry
                if last_entry_time is None or (
                    fr.timestamp_seconds - last_entry_time > cooldown_seconds
                ):
                    zone_cfg = zone_engine.get_zone_by_id(zone.id)
                    evt = BehaviourEvent(
                        event_id="",   # assigned later
                        video_id=video_id,
                        entity_id=track.entity_id,
                        track_id=track.track_id,
                        event_type="restricted_zone_entry",
                        severity="high",
                        start_time_seconds=fr.timestamp_seconds,
                        end_time_seconds=fr.timestamp_seconds,
                        duration_seconds=None,
                        zone_id=zone.id,
                        zone_name=zone_cfg.name if zone_cfg else zone.id,
                        confidence=0.0,   # filled by confidence.py
                        reason=(
                            f"{track.entity_id} entered the configured "
                            f"Restricted Zone '{zone_cfg.name if zone_cfg else zone.id}' "
                            f"at {_fmt_t(fr.timestamp_seconds)}."
                        ),
                        evidence={
                            "thresholds": {
                                "previous_zone_state": "outside",
                                "current_zone_state": "inside",
                                "reentry_cooldown_seconds": cooldown_seconds,
                            },
                            "observed_values": {
                                "entry_frame": fr.frame_number,
                                "entry_timestamp_seconds": fr.timestamp_seconds,
                            },
                            "track_stats": {
                                "duration_seconds": track.duration_seconds,
                                "observed_frames": track.observed_frames,
                            },
                        },
                        _det_confidences=[fr.detection_confidence],
                        _observed_frames=1,
                        _expected_frames=1,
                    )
                    events.append(evt)
                    last_entry_time = fr.timestamp_seconds

            last_inside = currently_inside

    return events


def _rule_loitering(
    track: TrackData,
    frames: list[FrameRecord],
    zone_engine: ZoneEngine,
    video_id: str,
    fps: float,
    loitering_duration_seconds: float,
    movement_window_seconds: float,
    max_speed_scaled: float,
) -> list[BehaviourEvent]:
    """Rule 3: loitering in a monitored zone.

    Speed metric: NET DISPLACEMENT over a rolling window (not path length).
    This avoids jitter inflating speed for stationary persons.
    See track_processor.py module docstring for the rationale.
    """
    events: list[BehaviourEvent] = []
    monitored_zones = [z for z in zone_engine.all_zones() if z.type == "monitored"]
    move_window_frames = max(1, int(movement_window_seconds * fps))

    for zone in monitored_zones:
        zone_cfg = zone_engine.get_zone_by_id(zone.id)
        zone_name = zone_cfg.name if zone_cfg else zone.id

        # Collect frames where person is stably inside this zone
        in_zone_frames = [
            fr for fr in frames
            if zone.id in getattr(fr, "_stable_zones", [])
        ]
        if not in_zone_frames:
            continue

        # Group into continuous intervals (gaps > MAX_GAP are already filled)
        intervals = _group_continuous(in_zone_frames, fps, max_gap_seconds=1.0)

        for interval_frames in intervals:
            if not interval_frames:
                continue

            start_fr  = interval_frames[0]
            end_fr    = interval_frames[-1]
            dwell_sec = end_fr.timestamp_seconds - start_fr.timestamp_seconds

            if dwell_sec < loitering_duration_seconds:
                continue  # Not long enough

            # Check average speed (net displacement in rolling window)
            avg_speed = _rolling_avg_speed(interval_frames, move_window_frames)
            if avg_speed > max_speed_scaled:
                continue  # Moving too much — not loitering

            # Find the exact frame when all conditions were first met
            detected_at = _find_loitering_detection_frame(
                interval_frames, fps, loitering_duration_seconds, max_speed_scaled,
                move_window_frames,
            )

            # Gather evidence data
            det_confs = [fr.detection_confidence for fr in interval_frames
                         if not fr.is_interpolated]
            obs_frames = len([fr for fr in interval_frames if not fr.is_interpolated])
            exp_frames = len(interval_frames)

            # Rule-evidence strength R:
            # combine dwell margin and speed margin
            dwell_margin = min(1.0, dwell_sec / (2 * loitering_duration_seconds))
            speed_margin = (
                1.0 - avg_speed / max_speed_scaled
                if max_speed_scaled > 0 else 1.0
            )
            r_strength = (dwell_margin + speed_margin) / 2.0

            evt = BehaviourEvent(
                event_id="",
                video_id=video_id,
                entity_id=track.entity_id,
                track_id=track.track_id,
                event_type="loitering",
                severity="medium",
                start_time_seconds=start_fr.timestamp_seconds,
                end_time_seconds=end_fr.timestamp_seconds,
                duration_seconds=round(dwell_sec, 2),
                zone_id=zone.id,
                zone_name=zone_name,
                confidence=0.0,
                reason=(
                    f"{track.entity_id} stayed in {zone_name} for "
                    f"{dwell_sec:.1f} seconds with average movement of "
                    f"{avg_speed:.1f} px/s, below the "
                    f"{max_speed_scaled:.1f} px/s threshold."
                ),
                evidence={
                    "thresholds": {
                        "dwell_threshold_seconds": loitering_duration_seconds,
                        "movement_threshold_px_per_second": max_speed_scaled,
                        "movement_window_seconds": movement_window_seconds,
                        "speed_metric": "net_displacement_per_window",
                    },
                    "observed_values": {
                        "observed_dwell_seconds": round(dwell_sec, 2),
                        "observed_average_speed_px_per_second": round(avg_speed, 2),
                        "detected_at_seconds": (
                            detected_at.timestamp_seconds if detected_at else None
                        ),
                    },
                    "track_stats": {
                        "duration_seconds": track.duration_seconds,
                        "observed_frames": track.observed_frames,
                    },
                },
                _det_confidences=det_confs,
                _observed_frames=obs_frames,
                _expected_frames=exp_frames,
            )
            # Store R for confidence computation
            evt.evidence["_r_strength"] = round(r_strength, 4)
            events.append(evt)

    return events


def _rule_wrong_direction(
    track: TrackData,
    frames: list[FrameRecord],
    zone_engine: ZoneEngine,
    video_id: str,
    fps: float,
    min_travel_scaled: float,
) -> list[BehaviourEvent]:
    """Rule 4: reverse travel in a directional zone.

    Uses smoothed x (for left/right) or y (for up/down) positions.
    Accumulates net displacement opposite to allowed_direction.
    Triggers once per lane traversal segment.
    """
    events: list[BehaviourEvent] = []
    dir_zones = [z for z in zone_engine.all_zones() if z.type == "directional"]

    for zone in dir_zones:
        zone_cfg = zone_engine.get_zone_by_id(zone.id)
        zone_name = zone_cfg.name if zone_cfg else zone.id
        allowed_dir = zone.allowed_direction

        # Axis and sign for the allowed direction
        # e.g. left_to_right: axis=x, allowed positive delta
        axis = 0 if allowed_dir in ("left_to_right", "right_to_left") else 1
        allowed_sign = (
            1 if allowed_dir in ("left_to_right", "bottom_to_top") else -1
        )
        # Wait — bottom_to_top: y decreases as you go up, so allowed delta is negative
        # Let's re-define clearly:
        # left_to_right:  x increases -> allowed_sign = +1
        # right_to_left:  x decreases -> allowed_sign = -1
        # top_to_bottom:  y increases -> allowed_sign = +1
        # bottom_to_top:  y decreases -> allowed_sign = -1
        if allowed_dir == "left_to_right":
            axis, allowed_sign = 0, +1
        elif allowed_dir == "right_to_left":
            axis, allowed_sign = 0, -1
        elif allowed_dir == "top_to_bottom":
            axis, allowed_sign = 1, +1
        elif allowed_dir == "bottom_to_top":
            axis, allowed_sign = 1, -1

        in_zone_frames = [
            fr for fr in frames
            if zone.id in getattr(fr, "_stable_zones", [])
        ]
        if len(in_zone_frames) < 2:
            continue

        # Accumulate reverse travel along the axis using smoothed positions
        pts = [fr.smoothed_center[axis] for fr in in_zone_frames]
        deltas = [pts[i + 1] - pts[i] for i in range(len(pts) - 1)]

        # Reverse movement = delta opposite to allowed_sign
        reverse_deltas = [-d for d in deltas if d * allowed_sign < 0]
        total_reverse_px = sum(reverse_deltas) if reverse_deltas else 0.0

        if total_reverse_px < min_travel_scaled:
            continue  # Not enough reverse travel

        start_fr = in_zone_frames[0]
        end_fr   = in_zone_frames[-1]

        det_confs = [fr.detection_confidence for fr in in_zone_frames
                     if not fr.is_interpolated]
        obs_frames = len([fr for fr in in_zone_frames if not fr.is_interpolated])
        exp_frames = len(in_zone_frames)

        # R: proportional to how much reverse travel exceeds minimum
        r_strength = min(1.0, total_reverse_px / (2 * min_travel_scaled))

        evt = BehaviourEvent(
            event_id="",
            video_id=video_id,
            entity_id=track.entity_id,
            track_id=track.track_id,
            event_type="wrong_direction_movement",
            severity="medium",
            start_time_seconds=start_fr.timestamp_seconds,
            end_time_seconds=end_fr.timestamp_seconds,
            duration_seconds=round(
                end_fr.timestamp_seconds - start_fr.timestamp_seconds, 2
            ),
            zone_id=zone.id,
            zone_name=zone_name,
            confidence=0.0,
            reason=(
                f"{track.entity_id} moved in the direction opposite to the "
                f"configured allowed direction ('{allowed_dir}') in "
                f"'{zone_name}', accumulating {total_reverse_px:.1f} px of "
                f"reverse travel (threshold: {min_travel_scaled:.1f} px)."
            ),
            evidence={
                "thresholds": {
                    "allowed_direction": allowed_dir,
                    "minimum_violation_distance_px": round(min_travel_scaled, 1),
                },
                "observed_values": {
                    "observed_direction": (
                        "right_to_left" if allowed_dir == "left_to_right"
                        else "left_to_right" if allowed_dir == "right_to_left"
                        else "bottom_to_top" if allowed_dir == "top_to_bottom"
                        else "top_to_bottom"
                    ),
                    "observed_reverse_travel_px": round(total_reverse_px, 1),
                },
                "track_stats": {
                    "duration_seconds": track.duration_seconds,
                    "observed_frames": track.observed_frames,
                },
            },
            _det_confidences=det_confs,
            _observed_frames=obs_frames,
            _expected_frames=exp_frames,
        )
        evt.evidence["_r_strength"] = round(r_strength, 4)
        events.append(evt)

    return events


def _rule_walkthrough(
    track: TrackData,
    frames: list[FrameRecord],
    zone_engine: ZoneEngine,
    video_id: str,
    fps: float,
    min_walk_seconds: float,
    existing_events: list[BehaviourEvent],
) -> list[BehaviourEvent]:
    """Rule 1: normal walkthrough in an allowed zone.

    Only fires if no OTHER events (medium/high) exist for this track.
    One info event per traversal per allowed zone.
    """
    # Check if any medium/high event already exists for this track
    has_unusual = any(
        e.track_id == track.track_id and e.severity != "info"
        for e in existing_events
    )

    events: list[BehaviourEvent] = []
    allowed_zones = [z for z in zone_engine.all_zones() if z.type == "allowed"]

    for zone in allowed_zones:
        zone_cfg = zone_engine.get_zone_by_id(zone.id)
        zone_name = zone_cfg.name if zone_cfg else zone.id

        in_zone_frames = [
            fr for fr in frames
            if zone.id in getattr(fr, "_stable_zones", [])
        ]
        if not in_zone_frames:
            continue

        intervals = _group_continuous(in_zone_frames, fps, max_gap_seconds=1.0)
        for interval_frames in intervals:
            if not interval_frames:
                continue
            start_fr = interval_frames[0]
            end_fr   = interval_frames[-1]
            dwell_sec = end_fr.timestamp_seconds - start_fr.timestamp_seconds

            if dwell_sec < min_walk_seconds:
                continue

            # Check average speed is above stationary threshold
            avg_speed = _rolling_avg_speed(interval_frames, max(1, int(fps * 0.5)))
            # Stationary threshold: below ~8 px/s at reference is stationary
            # For walkthrough, we want to confirm movement
            WALK_SPEED_MIN = 5.0  # px/s at reference (person must be walking)
            if avg_speed < WALK_SPEED_MIN:
                continue  # Person is stationary, not walking through

            det_confs = [fr.detection_confidence for fr in interval_frames
                         if not fr.is_interpolated]

            evt = BehaviourEvent(
                event_id="",
                video_id=video_id,
                entity_id=track.entity_id,
                track_id=track.track_id,
                event_type="normal_walkthrough",
                severity="info",
                start_time_seconds=start_fr.timestamp_seconds,
                end_time_seconds=end_fr.timestamp_seconds,
                duration_seconds=round(dwell_sec, 2),
                zone_id=zone.id,
                zone_name=zone_name,
                confidence=0.0,
                reason=(
                    f"{track.entity_id} walked through {zone_name} from "
                    f"{_fmt_t(start_fr.timestamp_seconds)} to "
                    f"{_fmt_t(end_fr.timestamp_seconds)}."
                ),
                evidence={
                    "thresholds": {
                        "min_walk_seconds": min_walk_seconds,
                    },
                    "observed_values": {
                        "traversal_seconds": round(dwell_sec, 2),
                        "average_speed_px_per_second": round(avg_speed, 2),
                    },
                    "track_stats": {
                        "duration_seconds": track.duration_seconds,
                    },
                },
                _det_confidences=det_confs,
                _observed_frames=len([fr for fr in interval_frames
                                      if not fr.is_interpolated]),
                _expected_frames=len(interval_frames),
            )
            evt.evidence["_r_strength"] = 0.7   # fixed for info events
            events.append(evt)

    return events


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _group_continuous(
    frames: list[FrameRecord],
    fps: float,
    max_gap_seconds: float = 1.0,
) -> list[list[FrameRecord]]:
    """Group a sorted list of frames into continuous intervals.

    Two consecutive frames are in the same interval if the gap between their
    frame_numbers is <= max_gap_seconds * fps.
    """
    if not frames:
        return []
    max_gap_frames = max(1, int(max_gap_seconds * fps))
    groups: list[list[FrameRecord]] = [[frames[0]]]
    for fr in frames[1:]:
        gap = fr.frame_number - groups[-1][-1].frame_number
        if gap <= max_gap_frames:
            groups[-1].append(fr)
        else:
            groups.append([fr])
    return groups


def _rolling_avg_speed(frames: list[FrameRecord], window_frames: int) -> float:
    """Compute mean net-displacement speed (px/s) over a rolling window.

    For each window, net displacement = Euclidean distance between first and last
    smoothed_center in the window.  Returns mean of all window speeds.
    Uses pre-computed speed_px_per_second values from track_processor.
    """
    if not frames:
        return 0.0
    # Use the per-frame speed already computed by track_processor (smoothed pts)
    speeds = [fr.speed_px_per_second for fr in frames]
    return float(np.mean(speeds)) if speeds else 0.0


def _find_loitering_detection_frame(
    frames: list[FrameRecord],
    fps: float,
    loitering_duration_seconds: float,
    max_speed_scaled: float,
    move_window_frames: int,
) -> FrameRecord | None:
    """Return the frame at which loitering conditions were FIRST satisfied.

    We scan forward: once dwell >= threshold AND avg_speed <= threshold,
    that is the 'detected_at' moment.
    """
    if not frames:
        return None
    start_ts = frames[0].timestamp_seconds
    for i, fr in enumerate(frames):
        dwell = fr.timestamp_seconds - start_ts
        if dwell < loitering_duration_seconds:
            continue
        window_frames_slice = frames[max(0, i - move_window_frames): i + 1]
        avg_speed = _rolling_avg_speed(window_frames_slice, move_window_frames)
        if avg_speed <= max_speed_scaled:
            return fr
    return frames[-1]


def _fmt_t(seconds: float) -> str:
    """Format timestamp as mm:ss.s"""
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:04.1f}"
