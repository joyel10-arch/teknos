"""
track_processor.py — Stage 2a: raw track records -> clean per-entity tracks.

WHAT: Takes the flat list of per-frame records from Stage 1 and:
  1. Groups them by track_id.
  2. Applies a moving-average smoother to bottom-centre points.
  3. Fills gaps shorter than MAX_GAP_SECONDS by linear interpolation.
  4. Marks tracks shorter than MIN_TRACK_SECONDS as invalid (no events allowed).
  5. Computes per-frame speed on SMOOTHED points.
  6. Packages each track as a TrackData dataclass.

WHY bottom-centre for position?  The bottom-centre of the bounding box is the
point closest to the ground-plane.  It is more stable for zone membership than
the box centre because it doesn't shift when the upper body is occluded, and it
is the conventional reference point for pedestrian trajectory analysis.

SPEED COMPUTATION — net displacement vs path length:
  We use NET DISPLACEMENT (Euclidean distance from first to last smoothed point
  in each rolling window) rather than total path length.
  Reason: at 640×360 with 8 FPS and YOLO box jitter of ±3–5 px, path-length
  inflates the apparent speed of stationary persons significantly.
  Net displacement underestimates speed for curved paths but is much more robust
  against jitter for detecting stationarity.  We document this trade-off here.

Known limitation: ID switches after occlusion (e.g., behind concrete columns) are
  NOT resolved.  One real person may appear as several short TrackData objects with
  different entity_ids.  Short-track filtering removes many ghost tracks but some
  legitimate persons may also be split.  This is reported in the summary stats as
  raw_track_ids vs valid_tracked_persons.  See docs/VIVA_NOTES.md.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FrameRecord:
    """One detection of a person in one frame (raw or interpolated)."""
    track_id: int
    entity_id: str
    frame_number: int
    timestamp_seconds: float
    bounding_box: list[float]           # [x1, y1, x2, y2]
    bottom_center: list[float]          # [x, y]  raw
    smoothed_center: list[float]        # [x, y]  after moving-average
    detection_confidence: float
    is_interpolated: bool = False       # True for gap-filled frames
    speed_px_per_second: float = 0.0   # computed from smoothed points


@dataclass
class TrackData:
    """All information about one tracked entity across the whole video."""
    track_id: int
    entity_id: str                      # "Person_<track_id>"
    frames: list[FrameRecord] = field(default_factory=list)

    # Quality flags
    is_valid_track: bool = True         # False if too short
    gap_frames: int = 0                 # total interpolated frames

    # Summary stats (populated by process_tracks)
    first_frame: int = 0
    last_frame: int = 0
    first_timestamp: float = 0.0
    last_timestamp: float = 0.0
    duration_seconds: float = 0.0
    observed_frames: int = 0            # actual detections (not interpolated)
    mean_detection_confidence: float = 0.0

    # Zone membership per frame is stored inside FrameRecord after zone_engine runs
    zones_visited: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def process_tracks(
    records: list[dict[str, Any]],
    fps: float,
    min_track_seconds: float = 1.0,
    max_gap_seconds: float = 1.0,
    smoothing_window_seconds: float = 0.4,
) -> tuple[list[TrackData], dict[str, int]]:
    """Convert raw per-frame records into clean TrackData objects.

    Parameters
    ----------
    records                : flat list of dicts from Stage 1 / cache
    fps                    : video frame rate (frames per second)
    min_track_seconds      : tracks shorter than this -> is_valid_track = False
    max_gap_seconds        : missing-frame gaps shorter than this are interpolated
    smoothing_window_seconds: half-width of the moving-average window (seconds)

    Returns
    -------
    (tracks, summary) where:
      tracks  : list of TrackData (all tracks, valid and invalid)
      summary : dict with raw_track_ids, valid_tracked_persons, short_tracks_filtered
    """
    # Convert threshold params to frame counts
    min_track_frames: int = max(1, int(min_track_seconds * fps))
    max_gap_frames: int = max(1, int(max_gap_seconds * fps))
    smooth_half: int = max(1, int(smoothing_window_seconds * fps / 2))

    # ── Group records by track_id ────────────────────────────────────────────
    by_id: dict[int, list[dict]] = defaultdict(list)
    for r in records:
        by_id[r["track_id"]].append(r)

    tracks: list[TrackData] = []

    for track_id, recs in by_id.items():
        # Sort by frame number (should already be sorted, but be safe)
        recs.sort(key=lambda r: r["frame_number"])
        entity_id = recs[0].get("entity_id") or f"Person #{track_id}"

        # ── Gap filling ──────────────────────────────────────────────────────
        filled = _fill_gaps(recs, max_gap_frames, fps)

        # ── Smoothing ────────────────────────────────────────────────────────
        _apply_smoothing(filled, smooth_half)

        # ── Speed computation ────────────────────────────────────────────────
        _compute_speed(filled, fps)

        # ── Build FrameRecord objects ────────────────────────────────────────
        frame_records = [
            FrameRecord(
                track_id=track_id,
                entity_id=entity_id,
                frame_number=r["frame_number"],
                timestamp_seconds=r["timestamp_seconds"],
                bounding_box=r.get("bounding_box", [0, 0, 0, 0]),
                bottom_center=r["bottom_center"],
                smoothed_center=r.get("smoothed_center", r["bottom_center"]),
                detection_confidence=r.get("detection_confidence", 0.0),
                is_interpolated=r.get("is_interpolated", False),
                speed_px_per_second=r.get("speed_px_per_second", 0.0),
            )
            for r in filled
        ]

        # ── Aggregate stats ──────────────────────────────────────────────────
        real_frames = [fr for fr in frame_records if not fr.is_interpolated]
        gap_frames_count = sum(1 for fr in frame_records if fr.is_interpolated)
        duration = (
            frame_records[-1].timestamp_seconds - frame_records[0].timestamp_seconds
            if len(frame_records) > 1 else 0.0
        )
        mean_conf = (
            float(np.mean([fr.detection_confidence for fr in real_frames]))
            if real_frames else 0.0
        )

        # ── Validity flag ────────────────────────────────────────────────────
        is_valid = len(real_frames) >= min_track_frames

        td = TrackData(
            track_id=track_id,
            entity_id=entity_id,
            frames=frame_records,
            is_valid_track=is_valid,
            gap_frames=gap_frames_count,
            first_frame=frame_records[0].frame_number,
            last_frame=frame_records[-1].frame_number,
            first_timestamp=frame_records[0].timestamp_seconds,
            last_timestamp=frame_records[-1].timestamp_seconds,
            duration_seconds=round(duration, 4),
            observed_frames=len(real_frames),
            mean_detection_confidence=round(mean_conf, 4),
        )
        tracks.append(td)

    # ── Summary stats ─────────────────────────────────────────────────────────
    raw_ids = len(tracks)
    valid_persons = sum(1 for t in tracks if t.is_valid_track)
    short_filtered = raw_ids - valid_persons

    summary = {
        "raw_track_ids": raw_ids,
        "valid_tracked_persons": valid_persons,
        "short_tracks_filtered": short_filtered,
        "min_track_seconds_threshold": min_track_seconds,
        "min_track_frames_threshold": min_track_frames,
    }
    logger.info(
        "Processed tracks: %d raw IDs, %d valid persons, %d short filtered",
        raw_ids, valid_persons, short_filtered,
    )
    return tracks, summary


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fill_gaps(
    recs: list[dict],
    max_gap_frames: int,
    fps: float,
) -> list[dict]:
    """Linear-interpolate bottom_centre across gaps <= max_gap_frames.

    Gaps wider than max_gap_frames are left as-is (the track appears to jump).
    Interpolated records are flagged with is_interpolated=True so they don't
    inflate detection confidence or frame counts.
    """
    if len(recs) < 2:
        return [dict(r, is_interpolated=False) for r in recs]

    filled: list[dict] = []
    for i, rec in enumerate(recs):
        filled.append(dict(rec, is_interpolated=False))
        if i < len(recs) - 1:
            gap = recs[i + 1]["frame_number"] - rec["frame_number"] - 1
            if 0 < gap <= max_gap_frames:
                # Linearly interpolate bottom_center over the gap
                bc0 = rec["bottom_center"]
                bc1 = recs[i + 1]["bottom_center"]
                for j in range(1, gap + 1):
                    t = j / (gap + 1)
                    fn = rec["frame_number"] + j
                    interp_x = bc0[0] + t * (bc1[0] - bc0[0])
                    interp_y = bc0[1] + t * (bc1[1] - bc0[1])
                    filled.append({
                        "track_id": rec["track_id"],
                        "entity_id": rec["entity_id"],
                        "frame_number": fn,
                        "timestamp_seconds": round(fn / fps, 4),
                        "bounding_box": rec["bounding_box"],  # carry last known box
                        "bottom_center": [round(interp_x, 2), round(interp_y, 2)],
                        "detection_confidence": 0.0,
                        "is_interpolated": True,
                    })
    return filled


def _apply_smoothing(recs: list[dict], half_window: int) -> None:
    """In-place: add 'smoothed_center' key using centred moving average.

    Window size = 2*half_window + 1 frames.  At boundaries the window shrinks.
    The smoothed value is used for speed/direction; the raw value is kept for
    zone membership (raw position is more accurate for boundary detection).
    """
    pts = np.array([r["bottom_center"] for r in recs], dtype=np.float32)
    n = len(pts)
    smoothed = np.zeros_like(pts)
    for i in range(n):
        lo = max(0, i - half_window)
        hi = min(n, i + half_window + 1)
        smoothed[i] = pts[lo:hi].mean(axis=0)
    for i, r in enumerate(recs):
        r["smoothed_center"] = [round(float(smoothed[i, 0]), 2),
                                 round(float(smoothed[i, 1]), 2)]


def _compute_speed(recs: list[dict], fps: float) -> None:
    """In-place: add 'speed_px_per_second' to each record.

    Uses net displacement (Euclidean distance between the smoothed positions at
    the edges of a rolling window) divided by the window duration, in px/s.
    Window = 5 frames (centred), trimmed at boundaries.

    Net displacement (not path length) is chosen because YOLO box jitter at
    640×360 inflates path length for stationary persons.  See module docstring.
    """
    pts = np.array([r["smoothed_center"] for r in recs], dtype=np.float32)
    n = len(pts)
    half = 2  # rolling window half-width (5 frames total)
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n - 1, i + half)
        if hi > lo:
            dist = float(np.linalg.norm(pts[hi] - pts[lo]))
            dur  = (hi - lo) / fps  # seconds
            speed = dist / dur if dur > 0 else 0.0
        else:
            speed = 0.0
        recs[i]["speed_px_per_second"] = round(speed, 4)
