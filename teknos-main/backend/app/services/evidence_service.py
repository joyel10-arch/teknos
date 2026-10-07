"""
evidence_service.py — Render evidence frame JPEGs for each event.

WHAT: For each BehaviourEvent, draws the person's bounding box, zone polygons,
      timestamp, and event label onto the frame at event start time, and saves
      it as a JPEG to the evidence_frames output directory.

WHY a separate service?  Evidence frames can be regenerated independently of
re-running YOLO.  They are pure draw operations on raw video + cached data.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from app.services.behaviour_engine import BehaviourEvent
from app.services.track_processor import TrackData
from app.services.zone_engine import ZoneEngine
from app.utils.time_utils import format_timestamp

logger = logging.getLogger(__name__)

# BGR colour palette
COLOUR_HIGH   = (0, 0, 220)      # red
COLOUR_MEDIUM = (0, 140, 255)    # amber/orange
COLOUR_INFO   = (180, 220, 0)    # cyan-green
COLOUR_ZONE   = (80, 200, 120)   # zone polygon outline
COLOUR_ZONE_RESTRICTED = (0, 0, 200)
COLOUR_ZONE_MONITORED  = (0, 165, 255)
COLOUR_ZONE_DIRECTIONAL = (200, 100, 0)


def draw_evidence_frame(
    event: BehaviourEvent,
    video_path: Path,
    tracks_by_id: dict[int, TrackData],
    zone_engine: ZoneEngine,
    output_dir: Path,
    jpeg_quality: int = 90,
) -> str | None:
    """Read the frame at event start time, annotate it, save JPEG.

    Returns the saved file path as a string, or None on failure.
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which frame to use
    # For loitering: use detected_at_seconds if available
    ts = event.start_time_seconds
    if event.event_type == "loitering":
        detected_at = (
            event.evidence.get("observed_values", {}).get("detected_at_seconds")
        )
        if detected_at is not None:
            ts = float(detected_at)

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    target_frame = int(ts * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        logger.warning("Could not read frame %d for event %s", target_frame, event.event_id)
        return None

    # ── Draw zone polygons ────────────────────────────────────────────────────
    for zone in zone_engine.all_zones():
        poly = zone_engine.scaled_polygon(zone.id)
        if not poly:
            continue
        pts = np.array(poly, dtype=np.int32).reshape((-1, 1, 2))

        zone_colour = {
            "restricted":  COLOUR_ZONE_RESTRICTED,
            "monitored":   COLOUR_ZONE_MONITORED,
            "directional": COLOUR_ZONE_DIRECTIONAL,
        }.get(zone.type, COLOUR_ZONE)

        # Semi-transparent fill
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], zone_colour)
        cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
        cv2.polylines(frame, [pts], isClosed=True, color=zone_colour, thickness=2)

        # Zone label
        cx = int(np.mean([p[0] for p in poly]))
        cy = int(np.mean([p[1] for p in poly]))
        cv2.putText(frame, zone.name, (cx - 40, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, zone_colour, 1, cv2.LINE_AA)

    # ── Draw person bounding box ──────────────────────────────────────────────
    track = tracks_by_id.get(event.track_id)
    if track:
        # Find the frame record closest to ts
        frame_rec = min(
            track.frames,
            key=lambda fr: abs(fr.timestamp_seconds - ts),
            default=None,
        )
        if frame_rec:
            x1, y1, x2, y2 = [int(v) for v in frame_rec.bounding_box]
            evt_colour = {
                "high":   COLOUR_HIGH,
                "medium": COLOUR_MEDIUM,
                "info":   COLOUR_INFO,
            }.get(event.severity, COLOUR_INFO)

            cv2.rectangle(frame, (x1, y1), (x2, y2), evt_colour, 3)

            # Label above box
            label = f"{event.entity_id}  [{event.event_type.replace('_', ' ')}]"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 4, y1), evt_colour, -1)
            cv2.putText(frame, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    # ── Timestamp overlay ─────────────────────────────────────────────────────
    time_str = f"Event: {event.event_id}  |  {format_timestamp(ts)}"
    cv2.putText(frame, time_str, (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

    # ── Event reason (bottom of frame) ────────────────────────────────────────
    reason_short = event.reason[:90] + ("..." if len(event.reason) > 90 else "")
    h = frame.shape[0]
    cv2.rectangle(frame, (0, h - 35), (frame.shape[1], h), (30, 30, 30), -1)
    cv2.putText(frame, reason_short, (8, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1, cv2.LINE_AA)

    # ── Save JPEG ─────────────────────────────────────────────────────────────
    out_path = output_dir / f"{event.event_id}.jpg"
    cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    logger.info("Evidence frame saved: %s", out_path)
    return str(out_path)


def generate_all_evidence_frames(
    events: list[BehaviourEvent],
    video_path: Path,
    tracks: list[TrackData],
    zone_engine: ZoneEngine,
    output_dir: Path,
    jpeg_quality: int = 90,
) -> None:
    """Generate evidence frames for every event. Updates event.evidence_frame_path."""
    tracks_by_id = {t.track_id: t for t in tracks}
    for evt in events:
        path = draw_evidence_frame(
            event=evt,
            video_path=video_path,
            tracks_by_id=tracks_by_id,
            zone_engine=zone_engine,
            output_dir=output_dir,
            jpeg_quality=jpeg_quality,
        )
        if path:
            evt.evidence_frame_path = path
