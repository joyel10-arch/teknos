r"""
b1_experiment.py — Phase B1 tracker config experiment.

Compares 4 configurations on the first 400 frames of avenue_test_01.avi:
  A) default tracker (bytetrack.yaml), imgsz=640
  B) custom tracker config,            imgsz=640
  C) default tracker,                  imgsz=960
  D) custom tracker config,            imgsz=960

Reports for each: unique IDs, short-track count (< 15 frames and < MIN_TRACK_FRAMES),
processing FPS, and processing time.

Run: sw/Scripts/python.exe scripts/b1_experiment.py
"""
from __future__ import annotations
import sys, time, json
from pathlib import Path
from collections import defaultdict

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import settings
from app.services.detector_tracker import run_detection_and_tracking

VIDEO = settings.PROJECT_ROOT / "datasets" / "videos" / "avenue_test_01.avi"
CACHE_DIR = settings.resolve(settings.TRACKS_CACHE_DIR)
CUSTOM_CFG = str(settings.resolve(settings.TRACKER_CONFIG))
MAX_FRAMES = 400
MIN_TRACK_FRAMES = 8   # < 1 s at ~8 FPS (approximately MIN_TRACK_SECONDS)

configs = [
    ("A_default_640",  "bytetrack.yaml", 640),
    ("B_custom_640",   CUSTOM_CFG,        640),
    ("C_default_960",  "bytetrack.yaml", 960),
    ("D_custom_960",   CUSTOM_CFG,        960),
]

print(f"\n{'='*70}")
print(f"Phase B1 Experiment: first {MAX_FRAMES} frames of {VIDEO.name}")
print(f"{'='*70}")
print(f"{'Label':<18} {'UniqueIDs':>9} {'Short<15f':>10} {'Short<8f':>9} {'FPS':>7} {'Time(s)':>9}")
print("-"*70)

for label, tracker, imgsz in configs:
    cache = CACHE_DIR / f"exp_{label}.json"
    if cache.exists():
        cache.unlink()   # always fresh for the experiment

    t0 = time.perf_counter()
    meta = run_detection_and_tracking(
        video_path=VIDEO,
        cache_path=cache,
        model_name=settings.YOLO_MODEL,
        fallback_model=settings.YOLO_FALLBACK_MODEL,
        conf=settings.YOLO_CONF,
        imgsz=imgsz,
        tracker_config=tracker,
        device=settings.DEVICE,
        max_frames=MAX_FRAMES,
        progress_callback=None,
    )
    elapsed = time.perf_counter() - t0

    # Count per-track frame counts
    with cache.open() as f:
        records = json.load(f)["records"]
    frames_per_id: dict[int, int] = defaultdict(int)
    for r in records:
        frames_per_id[r["track_id"]] += 1

    unique_ids = len(frames_per_id)
    short_15  = sum(1 for n in frames_per_id.values() if n < 15)
    short_8   = sum(1 for n in frames_per_id.values() if n < MIN_TRACK_FRAMES)
    fps_real  = meta["processing_fps"]

    print(f"{label:<18} {unique_ids:>9} {short_15:>10} {short_8:>9} {fps_real:>7.1f} {elapsed:>9.1f}")

print("="*70)
print("Done. Choose defaults from above results.")
