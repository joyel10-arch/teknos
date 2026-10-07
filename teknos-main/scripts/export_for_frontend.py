"""
export_for_frontend.py -- Copy pipeline outputs into frontend/public/demo/.

Writes:
  summary.json   -- video + track + event counts, processing info, disclaimer
  events.json    -- full event objects sorted by start time
  tracks.json    -- per-entity summary rows
  zones.json     -- zone config (minus internal _justification keys)
  annotated.mp4  -- H.264 annotated video
  evidence/<event_id>.jpg  -- one JPEG per event

Run from project root (sw venv active):
  python scripts/export_for_frontend.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import settings
from app.services.track_processor import process_tracks

CACHE_PATH = settings.resolve(settings.TRACKS_CACHE_DIR) / (
    "avenue_test_01__yolo11n_pt__conf25__imgsz640__maxfall_tracks.json"
)
ZONE_PATH   = settings.PROJECT_ROOT / "datasets" / "zones" / "avenue_walkway_zones.json"
REPORTS_DIR = settings.resolve(settings.REPORTS_DIR)
EVIDENCE_DIR = settings.resolve(settings.EVIDENCE_FRAMES_DIR)
ANNOTATED_DIR = settings.resolve(settings.ANNOTATED_VIDEOS_DIR)

FRONTEND_DEMO = settings.PROJECT_ROOT / "frontend" / "public" / "demo"
(FRONTEND_DEMO / "evidence").mkdir(parents=True, exist_ok=True)

VIDEO_ID = "avenue_test_01"

with CACHE_PATH.open() as f:
    cache = json.load(f)
meta = cache["metadata"]
records = cache["records"]

FPS = meta["fps"]
WIDTH, HEIGHT = meta["width"], meta["height"]
FRAME_COUNT = meta["frames_processed"]

tracks, summary = process_tracks(
    records, fps=FPS,
    min_track_seconds=settings.MIN_TRACK_SECONDS,
    max_gap_seconds=settings.MAX_GAP_SECONDS,
    smoothing_window_seconds=settings.SMOOTHING_WINDOW_SECONDS,
)

# Load events from report
events_src = REPORTS_DIR / f"{VIDEO_ID}_events.json"
if not events_src.exists():
    print(f"ERROR: {events_src} not found -- run run_full_pipeline.py first")
    sys.exit(1)
events_data = json.loads(events_src.read_text())
events_data.sort(key=lambda e: e["start_time_seconds"])

from collections import Counter
by_type = Counter(e["event_type"] for e in events_data)
by_sev  = Counter(e["severity"]   for e in events_data)

DISCLAIMER = (
    "Events are produced by trajectory-based rule detection operating on "
    "cached YOLO+ByteTrack outputs. Evidence Confidence (C) quantifies how "
    "well the tracking evidence supports each rule, not intent or risk. "
    "Zones were placed by us on this clip."
)

ALL_RULE_TYPES = [
    "normal_walkthrough", "restricted_zone_entry",
    "loitering", "wrong_direction_movement",
]

summary_dict = {
    "video_id": VIDEO_ID,
    "video_filename": "avenue_test_01.avi",
    "duration_seconds": round(FRAME_COUNT / FPS, 2),
    "fps": FPS,
    "resolution": {"width": WIDTH, "height": HEIGHT},
    "raw_track_ids": summary["raw_track_ids"],
    "valid_tracked_persons": summary["valid_tracked_persons"],
    "short_tracks_filtered": summary["short_tracks_filtered"],
    "min_track_seconds": settings.MIN_TRACK_SECONDS,
    "event_counts_by_type": {rt: by_type.get(rt, 0) for rt in ALL_RULE_TYPES},
    "event_counts_by_severity": dict(by_sev),
    "total_events": len(events_data),
    "processing_info": {
        "model_name": meta["model_name"],
        "detection_conf": meta["conf"],
        "imgsz": meta["imgsz"],
        "tracker_config": str(meta["tracker_config"]),
        "processing_fps": meta["processing_fps"],
        "processing_seconds": meta["processing_seconds"],
        "cache_path": str(CACHE_PATH),
    },
    "disclaimer": DISCLAIMER,
}
(FRONTEND_DEMO / "summary.json").write_text(json.dumps(summary_dict, indent=2))

# events.json
(FRONTEND_DEMO / "events.json").write_text(
    json.dumps(events_data, indent=2, default=str)
)

# tracks.json
tracks_out = []
for t in sorted(tracks, key=lambda t: t.track_id):
    xs = [fr.bottom_center[0] for fr in t.frames]
    ys = [fr.bottom_center[1] for fr in t.frames]
    tracks_out.append({
        "track_id": t.track_id,
        "entity_id": t.entity_id,
        "is_valid_track": t.is_valid_track,
        "first_timestamp": t.first_timestamp,
        "last_timestamp": t.last_timestamp,
        "duration_seconds": t.duration_seconds,
        "observed_frames": t.observed_frames,
        "gap_frames": t.gap_frames,
        "mean_detection_confidence": t.mean_detection_confidence,
        "x_range": [round(min(xs), 1), round(max(xs), 1)] if xs else [],
        "y_range": [round(min(ys), 1), round(max(ys), 1)] if ys else [],
        "net_dx": round(xs[-1] - xs[0], 1) if len(xs) > 1 else 0.0,
    })
(FRONTEND_DEMO / "tracks.json").write_text(json.dumps(tracks_out, indent=2))

# zones.json (strip _justification)
zone_data = json.loads(ZONE_PATH.read_text())
for z in zone_data.get("zones", []):
    z.pop("_justification", None)
(FRONTEND_DEMO / "zones.json").write_text(json.dumps(zone_data, indent=2))

# annotated.mp4
src_mp4 = ANNOTATED_DIR / f"{VIDEO_ID}_annotated.mp4"
if src_mp4.exists():
    shutil.copy2(src_mp4, FRONTEND_DEMO / "annotated.mp4")
else:
    print(f"WARNING: {src_mp4} not found")

# evidence/<event_id>.jpg
ev_dir = FRONTEND_DEMO / "evidence"
copied = 0
for e in events_data:
    eid = e["event_id"]
    src = EVIDENCE_DIR / f"{eid}.jpg"
    if src.exists():
        shutil.copy2(src, ev_dir / f"{eid}.jpg")
        copied += 1

print("Export complete.")
print(f"  summary.json   : {(FRONTEND_DEMO / 'summary.json').stat().st_size} bytes")
print(f"  events.json    : {(FRONTEND_DEMO / 'events.json').stat().st_size} bytes  ({len(events_data)} events)")
print(f"  tracks.json    : {(FRONTEND_DEMO / 'tracks.json').stat().st_size} bytes  ({len(tracks_out)} tracks)")
print(f"  zones.json     : {(FRONTEND_DEMO / 'zones.json').stat().st_size} bytes")
dst_mp4 = FRONTEND_DEMO / "annotated.mp4"
if dst_mp4.exists():
    print(f"  annotated.mp4  : {dst_mp4.stat().st_size // 1024} KB")
print(f"  evidence/      : {copied} frames copied")
