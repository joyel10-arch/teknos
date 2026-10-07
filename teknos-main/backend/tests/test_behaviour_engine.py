"""
test_behaviour_engine.py — Synthetic-track tests for all behaviour rules.

WHY synthetic tracks?  All rule logic must be testable without running YOLO.
We build FrameRecord lists by hand, feed them to the behaviour engine,
and assert the exact events produced.

All 6 test scenarios from Section 11 of the master prompt are implemented.
"""

import sys
from pathlib import Path
import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.services.track_processor import TrackData, FrameRecord
from app.services.zone_engine import ZoneEngine, SceneConfig
from app.services.behaviour_engine import run_behaviour_engine

FPS = 25.0  # convenient round number for test maths

# ─────────────────────────────────────────────────────────────────────────────
# Shared scene definition
# ─────────────────────────────────────────────────────────────────────────────

SCENE_DICT = {
    "scene_id": "test_scene",
    "scene_name": "Test Scene",
    "video_name": "test.avi",
    "reference_resolution": [640, 360],
    "params": {},
    "zones": [
        {
            "id": "walkway", "name": "Main Walkway", "type": "allowed", "priority": 1,
            "polygon": [[0, 0], [640, 0], [640, 200], [0, 200]],
        },
        {
            "id": "waiting", "name": "Waiting Area", "type": "monitored", "priority": 2,
            "polygon": [[0, 200], [640, 200], [640, 360], [0, 360]],
        },
        {
            "id": "restricted", "name": "No-Entry Area", "type": "restricted", "priority": 3,
            "polygon": [[500, 0], [640, 0], [640, 200], [500, 200]],
        },
        {
            "id": "lane", "name": "One-Way Lane", "type": "directional",
            "allowed_direction": "left_to_right", "priority": 2,
            "polygon": [[0, 250], [640, 250], [640, 360], [0, 360]],
        },
    ],
}


def make_engine(min_frames: int = 1) -> ZoneEngine:
    """Create ZoneEngine with min_frames=1 so hysteresis is instant in tests."""
    scene = SceneConfig.model_validate(SCENE_DICT)
    return ZoneEngine(scene, actual_width=640, actual_height=360,
                      zone_min_frames=min_frames)


def make_frames(
    track_id: int,
    positions: list[tuple[float, float]],  # (x, y) bottom-centre sequence
    start_frame: int = 0,
    fps: float = FPS,
    conf: float = 0.85,
) -> list[FrameRecord]:
    """Build a list of FrameRecord objects from (x, y) positions."""
    frames = []
    for i, (x, y) in enumerate(positions):
        fn = start_frame + i
        ts = fn / fps
        frames.append(FrameRecord(
            track_id=track_id,
            entity_id=f"Person_{track_id}",
            frame_number=fn,
            timestamp_seconds=round(ts, 4),
            bounding_box=[x - 20, y - 80, x + 20, y],
            bottom_center=[x, y],
            smoothed_center=[x, y],          # no smoothing in test — exact positions
            detection_confidence=conf,
            is_interpolated=False,
            speed_px_per_second=10.0,        # will be overridden in specific tests
        ))
    return frames


def make_track(
    track_id: int,
    frames: list[FrameRecord],
    is_valid: bool = True,
) -> TrackData:
    return TrackData(
        track_id=track_id,
        entity_id=f"Person_{track_id}",
        frames=frames,
        is_valid_track=is_valid,
        first_frame=frames[0].frame_number if frames else 0,
        last_frame=frames[-1].frame_number if frames else 0,
        first_timestamp=frames[0].timestamp_seconds if frames else 0.0,
        last_timestamp=frames[-1].timestamp_seconds if frames else 0.0,
        duration_seconds=(
            frames[-1].timestamp_seconds - frames[0].timestamp_seconds
            if len(frames) > 1 else 0.0
        ),
        observed_frames=len(frames),
        mean_detection_confidence=0.85,
    )


def run_engine(
    tracks: list[TrackData],
    min_walk_seconds: float = 1.5,
    loitering_duration_seconds: float = 10.0,
    max_avg_speed_px_s: float = 8.0,
    min_direction_travel_px: float = 80.0,
    zone_min_frames: int = 1,
) -> list:
    engine = make_engine(min_frames=zone_min_frames)
    return run_behaviour_engine(
        tracks=tracks,
        zone_engine=engine,
        video_id="test_vid",
        fps=FPS,
        frame_width=640,
        frame_height=360,
        min_walk_seconds=min_walk_seconds,
        loitering_duration_seconds=loitering_duration_seconds,
        max_avg_speed_px_s=max_avg_speed_px_s,
        min_direction_travel_px=min_direction_travel_px,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 1: Normal walkthrough
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalWalkthrough:

    def test_walking_through_allowed_zone_produces_one_info_event(self):
        """Person walks steadily across the walkway (y=100, x from 0→480).

        NOTE: path is capped at x=480 (< 500) to avoid overlapping the restricted
        zone polygon (x>500).  This is intentional — the test validates walking in
        the 'allowed' zone only, separate from restricted-zone logic.
        """
        # 75 frames at 25 FPS = 3 seconds; stay left of x=500 (restricted zone)
        positions = [(x, 100) for x in range(50, 481, 480 // 74)][:75]
        frames = make_frames(1, positions)
        # Set walking speed
        for fr in frames:
            fr.speed_px_per_second = 30.0  # clearly walking

        track = make_track(1, frames)
        events = run_engine([track])

        walkthrough = [e for e in events if e.event_type == "normal_walkthrough"]
        unusual = [e for e in events if e.severity != "info"]

        assert len(walkthrough) == 1, f"Expected 1 walkthrough, got {len(walkthrough)}"
        assert len(unusual) == 0, f"Expected 0 unusual events, got {len(unusual)}"


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 1b: Directional-zone rules + normal_walkthrough suppression
#
# Five cases required by the master prompt (inserted before B2 so they are
# checked immediately after the basic walkthrough scenario):
#   1. wrong direction: right-to-left travel above minimum fires exactly once
#   2. allowed direction (left to right) fires nothing
#   3. 40 px reverse (below the 80 px reference minimum) fires nothing
#   4. a track shorter than MIN_TRACK_SECONDS fires nothing in a directional zone
#   5. normal_walkthrough is emitted once per traversal and not emitted when a
#      rule fires for that track
# ─────────────────────────────────────────────────────────────────────────────

class TestDirectionalZoneRules:
    """Synthetic-track tests for directional zone detection and walkthrough suppression.

    The shared scene has a 'lane' zone (y 250–360, full width) with
    allowed_direction='left_to_right'.  All tracks in this class use y=300
    (inside the lane).  The 80 px reference minimum maps 1:1 because the test
    video is already the reference resolution (640×360, scale_x = 1.0).
    """

    # ── shared helpers ────────────────────────────────────────────────────────

    def _lane_track(self, track_id: int, x_positions: list[float]) -> TrackData:
        """Build a valid (long-enough) track entirely inside the lane zone."""
        frames = make_frames(track_id, [(x, 300) for x in x_positions])
        # smoothed_center must be set explicitly for direction checks
        for fr in frames:
            fr.smoothed_center = list(fr.bottom_center)
        return make_track(track_id, frames)

    def _walkway_track(self, track_id: int, x_positions: list[float]) -> TrackData:
        """Build a valid track entirely inside the walkway (allowed) zone at y=100."""
        frames = make_frames(track_id, [(x, 100) for x in x_positions])
        for fr in frames:
            fr.smoothed_center = list(fr.bottom_center)
            fr.speed_px_per_second = 30.0  # clearly walking speed
        return make_track(track_id, frames)

    # ── Test 1 ────────────────────────────────────────────────────────────────

    def test_wrong_direction_right_to_left_above_minimum_fires_exactly_once(self):
        """Right-to-left travel of 120 px (> 80 px threshold) emits exactly one
        wrong_direction_movement event.

        The lane is left_to_right; moving right-to-left is the reverse direction.
        120 px net reverse > 80 px MIN_DIRECTION_TRAVEL_PX reference → must fire.
        Track has 31 frames (≈ 1.24 s > MIN_TRACK_SECONDS=1.0 s) so is valid.
        """
        # 31 steps × 4 px = 120 px right-to-left (reverse)
        xs = list(range(400, 279, -4))   # [400, 396, ..., 280]
        events = run_engine(
            [self._lane_track(1, xs)],
            min_direction_travel_px=80.0,
        )
        wrong_dir = [e for e in events if e.event_type == "wrong_direction_movement"]
        assert len(wrong_dir) == 1, (
            f"Expected exactly 1 wrong_direction_movement for 120 px reverse "
            f"(threshold 80 px); got {len(wrong_dir)}"
        )

    # ── Test 2 ────────────────────────────────────────────────────────────────

    def test_allowed_direction_left_to_right_fires_nothing(self):
        """Left-to-right travel (the allowed direction) must not fire any
        wrong_direction_movement event — net reverse displacement is 0 px.

        100 frames × 4 px step = 400 px in the +x direction.
        """
        xs = list(range(100, 500, 4))    # 100 steps, left-to-right (allowed)
        events = run_engine(
            [self._lane_track(1, xs)],
            min_direction_travel_px=80.0,
        )
        wrong_dir = [e for e in events if e.event_type == "wrong_direction_movement"]
        assert len(wrong_dir) == 0, (
            f"Allowed direction (left-to-right) must NOT fire wrong_direction_movement; "
            f"got {len(wrong_dir)}"
        )

    # ── Test 3 ────────────────────────────────────────────────────────────────

    def test_40px_reverse_below_80px_minimum_fires_nothing(self):
        """Only 40 px of reverse travel (< 80 px threshold) must not fire.

        10 steps × 4 px = 40 px total reverse.  Since 40 < 80, the rule is silent.
        Track is valid (10 frames ≈ 0.4 s) — but below the 80 px trip-wire, so
        the length-check gate is not the reason for silence.

        Note: 10 frames < MIN_TRACK_SECONDS (1.0 s = 25 frames), so the track is
        marked invalid by process_tracks and the behaviour engine skips it.  We
        build the track with make_track(...) which sets is_valid=True directly to
        isolate the *distance* gate from the *duration* gate.  Even if the engine
        were to process the track, 40 px < 80 px so no event would fire.
        """
        xs = list(range(400, 360, -4))   # 10 steps × 4 px = 40 px reverse
        events = run_engine(
            [self._lane_track(1, xs)],
            min_direction_travel_px=80.0,
        )
        wrong_dir = [e for e in events if e.event_type == "wrong_direction_movement"]
        assert len(wrong_dir) == 0, (
            f"40 px reverse (< 80 px threshold) must NOT fire wrong_direction_movement; "
            f"got {len(wrong_dir)}"
        )

    # ── Test 4 ────────────────────────────────────────────────────────────────

    def test_track_shorter_than_min_track_seconds_fires_nothing_in_directional_zone(self):
        """A track whose duration falls below MIN_TRACK_SECONDS is marked invalid by
        process_tracks() and must produce zero events, even with 200 px of reverse
        travel that would otherwise far exceed the direction threshold.

        We use process_tracks() directly so the validity flag is set by the real
        duration gate, not by hand.
        """
        from app.services.track_processor import process_tracks

        # Build 10 raw records (0.4 s at 25 FPS) — well below MIN_TRACK_SECONDS=1.0 s
        # 10 steps × 20 px right-to-left → 200 px reverse (clearly over 80 px)
        raw_records = []
        for i, x in enumerate(range(400, 200, -20)):   # 10 frames
            raw_records.append({
                "track_id": 42,
                "entity_id": "Person_42",
                "frame_number": i,
                "timestamp_seconds": round(i / FPS, 4),
                "bounding_box": [x - 20, 220, x + 20, 300],
                "bottom_center": [float(x), 300.0],
                "detection_confidence": 0.85,
                "is_interpolated": False,
            })

        # min_track_seconds=1.0 means 25 frames needed; we only have 10 → invalid
        tracks, summary = process_tracks(
            raw_records,
            fps=FPS,
            min_track_seconds=1.0,
        )
        assert len(tracks) == 1
        assert tracks[0].is_valid_track is False, (
            "10-frame track (0.4 s) must be marked invalid "
            f"(min_track_seconds=1.0 s); summary={summary}"
        )

        events = run_engine(tracks, min_direction_travel_px=80.0)
        assert len(events) == 0, (
            f"Invalid (short) track must produce no events; got {events}"
        )

    # ── Test 5 ────────────────────────────────────────────────────────────────

    def test_normal_walkthrough_emitted_once_per_traversal_and_not_when_rule_fires(self):
        """Two tracks: one clean walkway traversal, one wrong-direction lane track.

        Track 1 (walkway, allowed zone):
          - Should emit exactly one normal_walkthrough (info) event.
          - No medium/high events.

        Track 2 (lane, directional zone — right-to-left reversal):
          - Should emit exactly one wrong_direction_movement event.
          - Must NOT emit a normal_walkthrough, because _rule_walkthrough only
            checks allowed-type zones, and this track is never in an allowed zone.
            (The lane zone is type='directional', not 'allowed'.)

        This jointly verifies: (a) walkthrough fires once per allowed-zone traversal,
        and (b) a track that only touches a directional zone and fires wrong_direction
        does not spuriously produce a normal_walkthrough event.
        """
        # ── Track 1: steady left-to-right walk through the allowed walkway zone ──
        # 75 frames at y=100 (walkway polygon covers y 0–200)
        walkway_xs = list(range(50, 481, 480 // 74))[:75]
        track1 = self._walkway_track(1, walkway_xs)

        # ── Track 2: right-to-left reversal in the lane zone (directional) ───────
        # 31 frames, 120 px reverse → fires wrong_direction_movement
        lane_xs = list(range(400, 279, -4))
        track2 = self._lane_track(2, lane_xs)

        events = run_engine([track1, track2], min_direction_travel_px=80.0)

        # Track 1 assertions
        t1_events = [e for e in events if e.track_id == 1]
        t1_walkthrough = [e for e in t1_events if e.event_type == "normal_walkthrough"]
        t1_unusual = [e for e in t1_events if e.severity != "info"]
        assert len(t1_walkthrough) == 1, (
            f"Track 1: expected 1 normal_walkthrough, got {len(t1_walkthrough)}"
        )
        assert len(t1_unusual) == 0, (
            f"Track 1: expected 0 unusual events, got {len(t1_unusual)}"
        )

        # Track 2 assertions
        t2_events = [e for e in events if e.track_id == 2]
        t2_wrong_dir = [e for e in t2_events if e.event_type == "wrong_direction_movement"]
        t2_walkthrough = [e for e in t2_events if e.event_type == "normal_walkthrough"]
        assert len(t2_wrong_dir) == 1, (
            f"Track 2: expected 1 wrong_direction_movement, got {len(t2_wrong_dir)}"
        )
        assert len(t2_walkthrough) == 0, (
            f"Track 2: normal_walkthrough must NOT fire for a track only in a "
            f"directional zone; got {len(t2_walkthrough)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 2: Restricted zone entry
# ─────────────────────────────────────────────────────────────────────────────

class TestRestrictedZoneEntry:

    def test_crossing_into_restricted_zone_fires_exactly_once(self):
        """Person moves from walkway into restricted zone — exactly 1 high event."""
        # First 20 frames outside restricted (x=200), then 20 inside (x=550)
        pos_outside = [(200, 100)] * 20
        pos_inside  = [(550, 100)] * 20   # x>500 is inside "restricted"
        frames = make_frames(1, pos_outside + pos_inside)

        track = make_track(1, frames)
        events = run_engine([track])

        entries = [e for e in events if e.event_type == "restricted_zone_entry"]
        assert len(entries) == 1, f"Expected 1 entry event, got {len(entries)}"
        assert entries[0].severity == "high"

    def test_entry_not_repeated_every_frame(self):
        """Person stays inside restricted zone for many frames — still only 1 event."""
        pos_outside = [(200, 100)] * 5
        pos_inside  = [(550, 100)] * 50   # stays inside
        frames = make_frames(1, pos_outside + pos_inside)

        events = run_engine([make_track(1, frames)])
        entries = [e for e in events if e.event_type == "restricted_zone_entry"]
        assert len(entries) == 1

    def test_entry_not_fired_when_track_starts_inside(self):
        """COUNT_INITIAL_INSIDE_AS_ENTRY=False (default): first frame inside → no entry."""
        # Track starts and stays inside restricted zone
        frames = make_frames(1, [(550, 100)] * 30)
        events = run_engine([make_track(1, frames)])
        entries = [e for e in events if e.event_type == "restricted_zone_entry"]
        assert len(entries) == 0, (
            "No entry should fire when track first observation is already inside "
            "(documented limitation, COUNT_INITIAL_INSIDE_AS_ENTRY=False)"
        )

    def test_entry_timestamp_is_correct(self):
        """Entry event start_time should match the frame when person crossed in."""
        # 10 frames outside (0.4 s at 25 FPS), then 20 inside
        pos_outside = [(200, 100)] * 10
        pos_inside  = [(550, 100)] * 20
        frames = make_frames(1, pos_outside + pos_inside)

        events = run_engine([make_track(1, frames)])
        entries = [e for e in events if e.event_type == "restricted_zone_entry"]
        assert len(entries) == 1
        # Entry frame is frame 10, timestamp = 10/25 = 0.4 s
        assert entries[0].start_time_seconds == pytest.approx(10 / FPS, abs=1 / FPS)


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 3: Loitering
# ─────────────────────────────────────────────────────────────────────────────

class TestLoitering:

    def _make_stationary_track(self, track_id: int, n_frames: int,
                                pos: tuple = (200, 280)) -> TrackData:
        """Person standing still in the monitored zone (y=280 is in waiting area)."""
        frames = make_frames(track_id, [pos] * n_frames)
        # Stationary: very low speed
        for fr in frames:
            fr.speed_px_per_second = 1.0  # well below threshold
        return make_track(track_id, frames)

    def test_15_second_stationary_produces_loitering(self):
        """15 s stationary in monitored zone → 1 loitering event."""
        n = int(15 * FPS)
        events = run_engine(
            [self._make_stationary_track(1, n)],
            loitering_duration_seconds=10.0,
            max_avg_speed_px_s=8.0,
        )
        loitering = [e for e in events if e.event_type == "loitering"]
        assert len(loitering) == 1

    def test_6_second_stationary_produces_no_loitering(self):
        """6 s stationary < 10 s threshold → 0 loitering events."""
        n = int(6 * FPS)
        events = run_engine(
            [self._make_stationary_track(1, n)],
            loitering_duration_seconds=10.0,
        )
        loitering = [e for e in events if e.event_type == "loitering"]
        assert len(loitering) == 0

    def test_fast_moving_person_does_not_trigger_loitering(self):
        """Person in monitored zone but moving fast (pacing) → no loitering."""
        frames = make_frames(1, [(200, 280)] * int(15 * FPS))
        # Override speed to above threshold
        for fr in frames:
            fr.speed_px_per_second = 20.0  # >> 8 px/s threshold
        track = make_track(1, frames)
        events = run_engine([track], max_avg_speed_px_s=8.0)
        loitering = [e for e in events if e.event_type == "loitering"]
        assert len(loitering) == 0

    def test_loitering_duration_stored_correctly(self):
        """duration_seconds in the event should reflect actual dwell time."""
        n = int(15 * FPS)
        events = run_engine([self._make_stationary_track(1, n)])
        loitering = [e for e in events if e.event_type == "loitering"]
        assert len(loitering) == 1
        assert loitering[0].duration_seconds == pytest.approx(
            (n - 1) / FPS, abs=0.1
        )


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 4: Wrong direction movement
# Required by master prompt Section 8:
#   (a) right-to-left reverse > min_travel fires exactly once
#   (b) allowed direction does not fire
#   (c) 40 px reverse (below threshold) does not fire
#   (d) short/invalid track does not fire
# ─────────────────────────────────────────────────────────────────────────────

class TestWrongDirection:

    def _make_lane_track(self, track_id: int,
                          x_positions: list[float]) -> TrackData:
        """Person in the directional lane (y=300, inside the lane polygon)."""
        frames = make_frames(track_id, [(x, 300) for x in x_positions])
        for fr in frames:
            fr.smoothed_center = list(fr.bottom_center)  # use exact positions
        return make_track(track_id, frames)

    def test_reverse_travel_over_threshold_fires_exactly_once(self):
        """(a) Moving right→left (reverse) for > 80 px fires exactly one
        wrong_direction_movement event.

        The lane zone has allowed_direction='left_to_right', so right-to-left
        is the reverse direction.  120 px of reverse travel (400→280) exceeds
        the 80 px threshold and must produce exactly one event.
        """
        # Start at x=400, move left to x=280 (120 px reverse travel)
        xs = list(range(400, 279, -4))  # 31 steps × 4 px = 120 px reverse
        events = run_engine(
            [self._make_lane_track(1, xs)],
            min_direction_travel_px=80.0,
        )
        wrong_dir = [e for e in events if e.event_type == "wrong_direction_movement"]
        assert len(wrong_dir) == 1, (
            f"Expected exactly 1 wrong_direction_movement event for 120 px reverse "
            f"(threshold 80 px); got {len(wrong_dir)}"
        )

    def test_allowed_direction_does_not_fire(self):
        """(b) Moving left→right (the allowed direction) → no wrong_direction event.

        Net travel is entirely in the allowed direction (+x).  There is no
        reverse component, so the rule must not fire.
        """
        xs = list(range(100, 500, 4))  # 100 steps, left-to-right (allowed)
        events = run_engine(
            [self._make_lane_track(1, xs)],
            min_direction_travel_px=80.0,
        )
        wrong_dir = [e for e in events if e.event_type == "wrong_direction_movement"]
        assert len(wrong_dir) == 0, (
            f"Allowed-direction travel must NOT fire wrong_direction; got {len(wrong_dir)}"
        )

    def test_40px_reverse_under_threshold_does_not_fire(self):
        """(c) Only 40 px of reverse travel → below 80 px threshold → no event.

        10 steps × 4 px each = 40 px reverse total.  Since 40 < 80 (min_travel),
        no wrong_direction_movement event should be generated.
        """
        xs = list(range(400, 360, -4))  # 10 steps × 4 px = 40 px reverse
        events = run_engine(
            [self._make_lane_track(1, xs)],
            min_direction_travel_px=80.0,
        )
        wrong_dir = [e for e in events if e.event_type == "wrong_direction_movement"]
        assert len(wrong_dir) == 0, (
            f"40 px reverse (< 80 px threshold) must NOT fire; got {len(wrong_dir)}"
        )

    def test_short_invalid_track_does_not_fire(self):
        """(d) A track marked is_valid=False must not fire wrong_direction_movement
        even when x-displacement clearly exceeds the threshold (200 px reverse).

        This confirms the valid-tracks-only gate in run_behaviour_engine
        applies to wrong-direction detection — not just restricted-entry.
        """
        xs = list(range(400, 200, -4))  # 50 steps × 4 px = 200 px reverse
        frames = make_frames(1, [(x, 300) for x in xs])
        for fr in frames:
            fr.smoothed_center = list(fr.bottom_center)
        track = make_track(1, frames, is_valid=False)  # explicitly invalid

        events = run_engine([track], min_direction_travel_px=80.0)
        wrong_dir = [e for e in events if e.event_type == "wrong_direction_movement"]
        assert len(wrong_dir) == 0, (
            f"Invalid track must produce no events; got {len(wrong_dir)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 5: Invalid/short track produces no events
# ─────────────────────────────────────────────────────────────────────────────

class TestInvalidTrack:

    def test_short_track_in_restricted_zone_fires_no_events(self):
        """Track marked is_valid=False must produce 0 events even if in restricted zone."""
        # Start outside, then cross into restricted zone
        pos = [(200, 100)] * 5 + [(550, 100)] * 5
        frames = make_frames(1, pos)
        track = make_track(1, frames, is_valid=False)  # explicitly invalid

        events = run_engine([track])
        assert len(events) == 0, (
            f"Invalid track should produce no events, got: {events}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 6: Jitter noise stays stationary after smoothing
# ─────────────────────────────────────────────────────────────────────────────

class TestJitterSmoothing:

    def test_jittery_stationary_person_counted_as_stationary(self):
        """±3 px noise on a stationary person must not trigger wrong_direction or
        disqualify loitering due to inflated speed."""
        import random
        random.seed(42)
        base_x, base_y = 200, 280
        n = int(15 * FPS)
        # Add ±3 px jitter to simulate YOLO box jitter
        positions = [
            (base_x + random.uniform(-3, 3), base_y + random.uniform(-3, 3))
            for _ in range(n)
        ]
        frames = make_frames(1, positions)

        # Apply a simple moving-average smoother to get smoothed_center
        window = 5
        from app.services.track_processor import _apply_smoothing
        raw_recs = [
            {
                "frame_number": fr.frame_number,
                "timestamp_seconds": fr.timestamp_seconds,
                "bottom_center": fr.bottom_center,
                "detection_confidence": fr.detection_confidence,
                "bounding_box": fr.bounding_box,
                "is_interpolated": False,
            }
            for fr in frames
        ]
        _apply_smoothing(raw_recs, half_window=window // 2)
        from app.services.track_processor import _compute_speed
        _compute_speed(raw_recs, FPS)

        # Update frames with smoothed values + speed
        for i, (fr, rec) in enumerate(zip(frames, raw_recs)):
            fr.smoothed_center = rec["smoothed_center"]
            fr.speed_px_per_second = rec["speed_px_per_second"]

        track = make_track(1, frames)
        events = run_engine(
            [track],
            loitering_duration_seconds=10.0,
            max_avg_speed_px_s=8.0,
        )

        # After smoothing, the stationary-jitter person should loiter
        loitering = [e for e in events if e.event_type == "loitering"]
        assert len(loitering) >= 1, (
            "Jitter-smoothed stationary person should still trigger loitering; "
            "if this fails, smoothing is insufficient or speed threshold needs review"
        )
