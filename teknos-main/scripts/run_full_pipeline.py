"""
run_full_pipeline.py -- Steps 2-5 of the sprint:
  2. Behaviour engine on all valid cached tracks
  3. Evidence frames + annotated video (H.264 via imageio-ffmpeg)
  4. JSON + CSV reports
  5. Export for frontend (frontend/public/demo/)

Run from project root (sw venv active):
  python scripts/run_full_pipeline.py
"""
from __future__ import annotations

import csv
import dataclasses
import json
import logging
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import settings
from app.services.track_processor import process_tracks
from app.services.zone_engine import ZoneEngine, SceneConfig
from app.services.behaviour_engine import run_behaviour_engine, BehaviourEvent
from app.services.confidence import compute_all_confidences
from app.services.evidence_service import generate_all_evidence_frames

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_full_pipeline")

# -- Paths ------------------------------------------------------------------
CACHE_PATH = settings.resolve(settings.TRACKS_CACHE_DIR) / (
    "avenue_test_01__yolo11n_pt__conf25__imgsz640__maxfall_tracks.json"
)
VIDEO_PATH = settings.PROJECT_ROOT / "datasets" / "videos" / "avenue_test_01.avi"
ZONE_PATH  = settings.PROJECT_ROOT / "datasets" / "zones" / "avenue_walkway_zones.json"
VIDEO_ID   = "avenue_test_01"

OUTPUTS    = settings.resolve(settings.OUTPUTS_BASE)
EVIDENCE_DIR    = settings.resolve(settings.EVIDENCE_FRAMES_DIR)
REPORTS_DIR     = settings.resolve(settings.REPORTS_DIR)
ANNOTATED_DIR   = settings.resolve(settings.ANNOTATED_VIDEOS_DIR)
FRONTEND_DEMO   = settings.PROJECT_ROOT / "frontend" / "public" / "demo"

for d in (EVIDENCE_DIR, REPORTS_DIR, ANNOTATED_DIR, FRONTEND_DEMO,
          FRONTEND_DEMO / "evidence"):
    d.mkdir(parents=True, exist_ok=True)


# -- Helpers ----------------------------------------------------------------

def fmt_t(s: float) -> str:
    m = int(s // 60)
    return f"{m:02d}:{s - m * 60:04.1f}"


def event_to_dict(e: BehaviourEvent) -> dict:
    return {
        "event_id": e.event_id,
        "video_id": e.video_id,
        "entity_id": e.entity_id,
        "track_id": e.track_id,
        "event_type": e.event_type,
        "severity": e.severity,
        "start_time_seconds": e.start_time_seconds,
        "end_time_seconds": e.end_time_seconds,
        "duration_seconds": e.duration_seconds,
        "zone_id": e.zone_id,
        "zone_name": e.zone_name,
        "confidence": e.confidence,
        "reason": e.reason,
        "evidence": e.evidence,
        "evidence_frame_path": e.evidence_frame_path,
    }


# -----------------------------------------------------------------------------
# Stage 2 -- Load cache + process tracks
# -----------------------------------------------------------------------------
print("\n" + "=" * 65)
print(f"SafeWatch AI -- Full Pipeline  ({VIDEO_ID})")
print("=" * 65)
print("Stage 2a: Loading cache + processing tracks …")

t0 = time.perf_counter()
with CACHE_PATH.open() as f:
    cache = json.load(f)
meta_cache = cache["metadata"]
records = cache["records"]

FPS    = meta_cache["fps"]
WIDTH  = meta_cache["width"]
HEIGHT = meta_cache["height"]
FRAME_COUNT = meta_cache["frames_processed"]
VIDEO_DURATION = FRAME_COUNT / FPS

tracks, summary = process_tracks(
    records,
    fps=FPS,
    min_track_seconds=settings.MIN_TRACK_SECONDS,
    max_gap_seconds=settings.MAX_GAP_SECONDS,
    smoothing_window_seconds=settings.SMOOTHING_WINDOW_SECONDS,
)
print(
    f"  raw={summary['raw_track_ids']}  "
    f"valid={summary['valid_tracked_persons']}  "
    f"short_filtered={summary['short_tracks_filtered']} "
    f"(< {settings.MIN_TRACK_SECONDS}s)"
)

# -----------------------------------------------------------------------------
# Stage 2b -- Zone engine
# -----------------------------------------------------------------------------
print("Stage 2b: Loading zone config …")
scene = SceneConfig.model_validate(json.loads(ZONE_PATH.read_text()))
zone_engine = ZoneEngine(
    scene, actual_width=WIDTH, actual_height=HEIGHT,
    zone_min_frames=settings.ZONE_MIN_FRAMES,
)
print(f"  loaded {len(scene.zones)} zones")

# -----------------------------------------------------------------------------
# Stage 2c -- Behaviour engine
# -----------------------------------------------------------------------------
print("Stage 2c: Running behaviour engine …")
events = run_behaviour_engine(
    tracks=tracks,
    zone_engine=zone_engine,
    video_id=VIDEO_ID,
    fps=FPS,
    frame_width=WIDTH,
    frame_height=HEIGHT,
    min_walk_seconds=settings.MIN_WALK_SECONDS,
    loitering_duration_seconds=settings.LOITERING_DURATION_SECONDS,
    max_avg_speed_px_s=settings.MAX_AVERAGE_SPEED_PX_PER_SECOND,
    min_direction_travel_px=settings.MIN_DIRECTION_TRAVEL_PX,
)

compute_all_confidences(events)

# Count by type
from collections import Counter
by_type = Counter(e.event_type for e in events)
by_sev  = Counter(e.severity for e in events)

ALL_RULE_TYPES = [
    "normal_walkthrough", "restricted_zone_entry",
    "loitering", "wrong_direction_movement",
]

print("\n  -- Events by type ------------------------------------------")
for rt in ALL_RULE_TYPES:
    n = by_type.get(rt, 0)
    status = f"{n} event(s)" if n else "0 -- rule produced nothing on this clip"
    print(f"    {rt:35s}: {status}")

print("\n  -- Event details -------------------------------------------")
for e in events:
    print(
        f"    [{e.event_id}] {e.event_type:30s}  {e.severity:6s}  "
        f"{e.entity_id:12s}  zone={e.zone_id:15s}  "
        f"t={fmt_t(e.start_time_seconds)}  C={e.confidence:.2f}"
    )
    print(f"         reason: {e.reason[:100]}")

stage2_secs = time.perf_counter() - t0

# -----------------------------------------------------------------------------
# Stage 3a -- Evidence frames
# -----------------------------------------------------------------------------
print("\nStage 3a: Generating evidence frames …")
t3a = time.perf_counter()
generate_all_evidence_frames(
    events=events,
    video_path=VIDEO_PATH,
    tracks=tracks,
    zone_engine=zone_engine,
    output_dir=EVIDENCE_DIR,
    jpeg_quality=settings.EVIDENCE_JPEG_QUALITY,
)
print(f"  {len(events)} evidence frames in {time.perf_counter() - t3a:.1f}s")

# -----------------------------------------------------------------------------
# Stage 3b -- Annotated video (H.264 via imageio-ffmpeg)
# -----------------------------------------------------------------------------
print("Stage 3b: Rendering annotated video …")
t3b = time.perf_counter()

ANNOTATED_MP4 = ANNOTATED_DIR / f"{VIDEO_ID}_annotated.mp4"

# Zone colour palette
ZONE_COLOURS = {
    "allowed":     (180, 220,   0),
    "monitored":   (  0, 165, 255),
    "restricted":  (  0,   0, 200),
    "directional": (200, 100,   0),
}

# Build frame→events lookup
frame_events: dict[int, list[BehaviourEvent]] = {}
tracks_by_id = {t.track_id: t for t in tracks}

for evt in events:
    track = tracks_by_id.get(evt.track_id)
    if not track:
        continue
    for fr in track.frames:
        if evt.start_time_seconds <= fr.timestamp_seconds <= evt.end_time_seconds:
            frame_events.setdefault(fr.frame_number, []).append(evt)

# Build frame→bboxes lookup for all valid tracks
frame_boxes: dict[int, list[tuple]] = {}
for t in tracks:
    if not t.is_valid_track:
        continue
    for fr in t.frames:
        frame_boxes.setdefault(fr.frame_number, []).append(
            (t.track_id, t.entity_id, fr.bounding_box, fr.bottom_center)
        )

cap = cv2.VideoCapture(str(VIDEO_PATH))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# Try imageio-ffmpeg first; fall back to OpenCV writer
try:
    import imageio
    writer_mode = "imageio"
    writer_frames = []
    print("  using imageio-ffmpeg writer")
except ImportError:
    writer_mode = "cv2"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    cv_writer = cv2.VideoWriter(str(ANNOTATED_MP4), fourcc, FPS, (WIDTH, HEIGHT))
    print("  imageio not installed -- using cv2 mp4v fallback")

fn = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Draw zone overlays
    for zone in zone_engine.all_zones():
        poly = zone_engine.scaled_polygon(zone.id)
        if not poly:
            continue
        pts = np.array(poly, dtype=np.int32).reshape((-1, 1, 2))
        col = ZONE_COLOURS.get(zone.type, (80, 200, 120))
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], col)
        cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)
        cv2.polylines(frame, [pts], True, col, 1)
        cx = int(np.mean([p[0] for p in poly]))
        cy = int(np.mean([p[1] for p in poly]))
        cv2.putText(frame, zone.name, (cx - 40, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1, cv2.LINE_AA)

    # Draw bounding boxes for valid tracks
    for (tid, eid, bbox, bc) in frame_boxes.get(fn, []):
        x1, y1, x2, y2 = [int(v) for v in bbox]
        # Check if any active event on this frame
        active_evts = [e for e in frame_events.get(fn, []) if e.track_id == tid]
        if active_evts:
            sev = active_evts[0].severity
            col = {"high": (0,0,220), "medium": (0,140,255), "info": (180,220,0)}.get(sev, (200,200,200))
        else:
            col = (200, 200, 200)
        cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
        cv2.putText(frame, eid, (x1, max(0, y1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1, cv2.LINE_AA)
        # bottom-centre dot
        cv2.circle(frame, (int(bc[0]), int(bc[1])), 3, col, -1)

    # Event banner for this frame
    active = frame_events.get(fn, [])
    for i, evt in enumerate(active[:3]):
        label = f"[{evt.event_id}] {evt.event_type.replace('_', ' ')} -- {evt.entity_id}"
        cv2.putText(frame, label, (8, HEIGHT - 45 + i * 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 200), 1, cv2.LINE_AA)

    # Timestamp
    ts = fn / FPS
    cv2.putText(frame, f"{fmt_t(ts)}  f{fn}", (8, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    if writer_mode == "imageio":
        writer_frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    else:
        cv_writer.write(frame)

    fn += 1
    if fn % 200 == 0:
        print(f"  rendered {fn}/{total_frames} frames …", end="\r", flush=True)

cap.release()

if writer_mode == "imageio":
    print(f"  encoding {len(writer_frames)} frames with imageio …")
    imageio.mimwrite(str(ANNOTATED_MP4), writer_frames, fps=FPS,
                     codec="libx264", quality=None,
                     output_params=["-crf", "23", "-preset", "fast"])
else:
    cv_writer.release()

render_secs = time.perf_counter() - t3b
print(f"\n  annotated video: {ANNOTATED_MP4}  ({render_secs:.1f}s)")

# -----------------------------------------------------------------------------
# Stage 4 -- Reports (JSON + CSV)
# -----------------------------------------------------------------------------
print("\nStage 4: Writing reports …")

events_json_path = REPORTS_DIR / f"{VIDEO_ID}_events.json"
with events_json_path.open("w") as f:
    json.dump([event_to_dict(e) for e in events], f, indent=2, default=str)

events_csv_path = REPORTS_DIR / f"{VIDEO_ID}_events.csv"
csv_fields = [
    "event_id", "event_type", "severity", "entity_id", "track_id",
    "zone_id", "zone_name", "start_time_seconds", "end_time_seconds",
    "duration_seconds", "confidence", "reason",
]
with events_csv_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=csv_fields)
    w.writeheader()
    for e in events:
        w.writerow({k: getattr(e, k) for k in csv_fields})

print(f"  JSON report: {events_json_path}")
print(f"  CSV  report: {events_csv_path}")

# -----------------------------------------------------------------------------
# Stage 5 -- Export for frontend
# -----------------------------------------------------------------------------
print("\nStage 5: Exporting for frontend …")

# summary.json
DISCLAIMER = (
    "Events are produced by trajectory-based rule detection operating on "
    "cached YOLO+ByteTrack outputs. Evidence Confidence (C) quantifies how "
    "well the tracking evidence supports each rule, not intent or risk. "
    "Zones were placed by us on this clip."
)
processing_info = {
    "model_name": meta_cache["model_name"],
    "detection_conf": meta_cache["conf"],
    "imgsz": meta_cache["imgsz"],
    "tracker_config": str(meta_cache["tracker_config"]),
    "processing_fps": meta_cache["processing_fps"],
    "processing_seconds": meta_cache["processing_seconds"],
    "cache_path": str(CACHE_PATH),
}
summary_dict = {
    "video_id": VIDEO_ID,
    "video_filename": "avenue_test_01.avi",
    "duration_seconds": round(VIDEO_DURATION, 2),
    "fps": FPS,
    "resolution": {"width": WIDTH, "height": HEIGHT},
    "raw_track_ids": summary["raw_track_ids"],
    "valid_tracked_persons": summary["valid_tracked_persons"],
    "short_tracks_filtered": summary["short_tracks_filtered"],
    "min_track_seconds": settings.MIN_TRACK_SECONDS,
    "event_counts_by_type": {rt: by_type.get(rt, 0) for rt in ALL_RULE_TYPES},
    "event_counts_by_severity": dict(by_sev),
    "total_events": len(events),
    "processing_info": processing_info,
    "disclaimer": DISCLAIMER,
}
(FRONTEND_DEMO / "summary.json").write_text(json.dumps(summary_dict, indent=2))

# events.json
events_export = sorted([event_to_dict(e) for e in events],
                        key=lambda e: e["start_time_seconds"])
(FRONTEND_DEMO / "events.json").write_text(json.dumps(events_export, indent=2, default=str))

# tracks.json
tracks_export = []
for t in sorted(tracks, key=lambda t: t.track_id):
    xs = [fr.bottom_center[0] for fr in t.frames]
    ys = [fr.bottom_center[1] for fr in t.frames]
    tracks_export.append({
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
(FRONTEND_DEMO / "tracks.json").write_text(json.dumps(tracks_export, indent=2))

# zones.json -- strip internal _justification keys
zone_export = json.loads(ZONE_PATH.read_text())
for z in zone_export.get("zones", []):
    z.pop("_justification", None)
(FRONTEND_DEMO / "zones.json").write_text(json.dumps(zone_export, indent=2))

# annotated.mp4
dst_mp4 = FRONTEND_DEMO / "annotated.mp4"
shutil.copy2(ANNOTATED_MP4, dst_mp4)

# evidence/<event_id>.jpg
ev_dir = FRONTEND_DEMO / "evidence"
ev_dir.mkdir(exist_ok=True)
for e in events:
    src = Path(e.evidence_frame_path) if e.evidence_frame_path else None
    if src and src.exists():
        shutil.copy2(src, ev_dir / f"{e.event_id}.jpg")

# -----------------------------------------------------------------------------
# Final report
# -----------------------------------------------------------------------------
def kb(p: Path) -> str:
    return f"{p.stat().st_size / 1024:.1f} KB" if p.exists() else "MISSING"

print("\n" + "=" * 65)
print("PIPELINE COMPLETE -- File sizes")
print("=" * 65)
exported_files = [
    FRONTEND_DEMO / "summary.json",
    FRONTEND_DEMO / "events.json",
    FRONTEND_DEMO / "tracks.json",
    FRONTEND_DEMO / "zones.json",
    FRONTEND_DEMO / "annotated.mp4",
    events_json_path,
    events_csv_path,
]
for p in exported_files:
    print(f"  {str(p.relative_to(settings.PROJECT_ROOT)):60s}  {kb(p)}")

# Evidence frames
print(f"\n  Evidence frames ({len(events)} total):")
for e in events:
    src = ev_dir / f"{e.event_id}.jpg"
    print(f"    {e.event_id}  {kb(src)}")

total_wall = time.perf_counter() - t0
print(f"\nTotal pipeline wall-clock: {total_wall:.1f}s")
