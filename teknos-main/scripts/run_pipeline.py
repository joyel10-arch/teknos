"""
run_pipeline.py — CLI: run the SafeWatch AI pipeline on one video file.

Usage (from project root, with the sw venv active):
  python scripts/run_pipeline.py --video datasets/videos/avenue_test_01.avi
  python scripts/run_pipeline.py --video datasets/videos/avenue_test_01.avi --max-frames 400
  python scripts/run_pipeline.py --video datasets/videos/avenue_test_01.avi --force-rerun

This script orchestrates all pipeline stages.  In Phase B1, only Stage 1 is
implemented; later phases will fill in the remaining stages automatically via
the same entry point.

Assumption: run from the project root (E:\\safewatch) so that relative paths
from config.py resolve correctly.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# ── Add backend to sys.path so we can import from app ──────────────────────
BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import settings
from app.services.detector_tracker import run_detection_and_tracking, load_cache
from app.services.track_processor import process_tracks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_pipeline")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SafeWatch AI CLI pipeline runner")
    p.add_argument("--video", required=True, type=Path,
                   help="Path to input video file")
    p.add_argument("--model", default=settings.YOLO_MODEL,
                   help=f"YOLO model name (default: {settings.YOLO_MODEL})")
    p.add_argument("--conf", type=float, default=settings.YOLO_CONF,
                   help=f"Detection confidence threshold (default: {settings.YOLO_CONF})")
    p.add_argument("--imgsz", type=int, default=settings.YOLO_IMGSZ,
                   help=f"Inference image size (default: {settings.YOLO_IMGSZ})")
    p.add_argument("--tracker", default=str(settings.resolve(settings.TRACKER_CONFIG)),
                   help="ByteTrack YAML path or ultralytics built-in name")
    p.add_argument("--max-frames", type=int, default=None,
                   help="Only process this many frames (dev mode)")
    p.add_argument("--force-rerun", action="store_true",
                   help="Ignore existing cache and re-run Stage 1")
    p.add_argument("--stage", type=int, default=1,
                   help="Run up to this stage (1=detect+track, 2=analyse, 3=render)")
    return p.parse_args()


def progress_cb(current: int, total: int) -> None:
    pct = int(100 * current / total) if total else 0
    print(f"  Stage 1 — detecting: {current}/{total} frames ({pct}%)", end="\r",
          flush=True)


def main() -> None:
    args = parse_args()

    video_path = Path(args.video)
    if not video_path.is_absolute():
        video_path = settings.PROJECT_ROOT / video_path
    if not video_path.exists():
        logger.error("Video not found: %s", video_path)
        sys.exit(1)

    # Derive a safe cache filename from the video stem + params
    video_id = video_path.stem
    cache_name = (
        f"{video_id}"
        f"__{args.model.replace('.', '_')}"
        f"__conf{int(args.conf*100)}"
        f"__imgsz{args.imgsz}"
        f"__maxf{args.max_frames or 'all'}"
        f"_tracks.json"
    )
    cache_path = settings.resolve(settings.TRACKS_CACHE_DIR) / cache_name

    # ──────────────────────────────────────────────────────────────────────
    # Stage 1 — Detect + Track
    # ──────────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"SafeWatch AI Pipeline — {video_path.name}")
    print(f"{'='*60}")
    print(f"Stage 1: YOLO detection + ByteTrack")
    print(f"  model   = {args.model}")
    print(f"  conf    = {args.conf}")
    print(f"  imgsz   = {args.imgsz}")
    print(f"  tracker = {args.tracker}")
    print(f"  max_f   = {args.max_frames or 'all'}")
    print(f"  cache   = {cache_path}")

    if args.force_rerun and cache_path.exists():
        cache_path.unlink()
        print("  (cache deleted; re-running detection)")

    t1 = time.perf_counter()
    meta = run_detection_and_tracking(
        video_path=video_path,
        cache_path=cache_path,
        model_name=args.model,
        fallback_model=settings.YOLO_FALLBACK_MODEL,
        conf=args.conf,
        imgsz=args.imgsz,
        tracker_config=args.tracker,
        device=settings.DEVICE,
        max_frames=args.max_frames,
        progress_callback=progress_cb,
    )
    print()  # clear the \r progress line
    stage1_secs = time.perf_counter() - t1

    print(f"\n  ✓ Stage 1 complete in {stage1_secs:.1f}s")
    print(f"    frames processed : {meta['frames_processed']}")
    print(f"    unique track IDs : {meta['total_raw_track_ids']}")
    print(f"    total records    : {meta['total_records']}")
    print(f"    processing FPS   : {meta['processing_fps']}")

    if args.stage < 2:
        print("\nStage 1 only requested. Done.")
        return

    # ──────────────────────────────────────────────────────────────────────
    # Stage 2 — Track processing (quality filtering, smoothing)
    # ──────────────────────────────────────────────────────────────────────
    print(f"\nStage 2a: Track quality processing")
    _, records = load_cache(cache_path)
    t2 = time.perf_counter()
    tracks, summary = process_tracks(
        records=records,
        fps=meta["fps"],
        min_track_seconds=settings.MIN_TRACK_SECONDS,
        max_gap_seconds=settings.MAX_GAP_SECONDS,
        smoothing_window_seconds=settings.SMOOTHING_WINDOW_SECONDS,
    )
    stage2_secs = time.perf_counter() - t2

    print(f"  ✓ Stage 2a complete in {stage2_secs:.2f}s")
    print(f"    raw track IDs           : {summary['raw_track_ids']}")
    print(f"    valid tracked persons   : {summary['valid_tracked_persons']}")
    print(f"    short tracks filtered   : {summary['short_tracks_filtered']}"
          f"  (< {summary['min_track_seconds_threshold']}s)")

    print("\nAll done.")


if __name__ == "__main__":
    main()
