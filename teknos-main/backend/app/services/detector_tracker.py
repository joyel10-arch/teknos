"""
detector_tracker.py — Stage 1: YOLO person detection + ByteTrack.

WHAT: Iterates every frame of a video (stream=True, persist=True), runs YOLO
      person detection (class 0 only), and collects raw per-frame track records.
      Saves results to a JSON cache so Stage 2 can be re-run without re-running
      YOLO (which is slow ~8 FPS on CPU).

WHY THREE STAGES: YOLO on CPU is slow (~8 FPS).  Decoupling detection from
      analysis means zone tuning, rule tweaks, or threshold changes do NOT require
      re-running the expensive inference step.

Cache invalidation: the cache stores the params used (model, conf, imgsz, tracker
      config path) alongside the data.  If the caller passes different params the
      cache is considered stale and detection is re-run.

Output format (one record per detected person per frame):
  {
    "track_id": int,
    "entity_id": "Person_<track_id>",
    "frame_number": int,
    "timestamp_seconds": float,      # frame_number / fps
    "bounding_box": [x1, y1, x2, y2],
    "bottom_center": [x, y],         # ((x1+x2)/2, y2) — used for zone membership
    "detection_confidence": float
  }
Zone membership is NOT added here; it is added in track_processor after zone loading.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

import cv2
from ultralytics import YOLO

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def run_detection_and_tracking(
    video_path: Path,
    cache_path: Path,
    model_name: str = "yolo11n.pt",
    fallback_model: str = "yolov8n.pt",
    conf: float = 0.25,
    imgsz: int = 640,
    tracker_config: Path | str = "bytetrack.yaml",
    device: str = "cpu",
    max_frames: int | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Run YOLO+ByteTrack on *video_path*, save cache to *cache_path*, return metadata.

    Parameters
    ----------
    video_path       : input video file
    cache_path       : where to write / read the JSON cache
    model_name       : YOLO model filename (must be on PATH or in project root)
    fallback_model   : used if model_name cannot be loaded
    conf             : YOLO detection confidence threshold
    imgsz            : inference image size (px)
    tracker_config   : path to ByteTrack YAML or Ultralytics built-in name
    device           : "cpu" always for this hardware
    max_frames       : dev option — stop after this many frames (None = full video)
    progress_callback: called with (current_frame, total_frames) every 30 frames

    Returns
    -------
    dict with keys: fps, width, height, frame_count, model_name, conf, imgsz,
                    tracker_config, total_tracks, records_count, cache_path
    """
    video_path = Path(video_path)
    cache_path = Path(cache_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    # ── Read video metadata ──────────────────────────────────────────────────
    cap = cv2.VideoCapture(str(video_path))
    fps: float = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width: int = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height: int = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames: int = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    if fps <= 0 or width == 0 or height == 0:
        raise ValueError(f"Cannot read video properties from {video_path}")

    effective_total = min(total_frames, max_frames) if max_frames else total_frames
    tracker_config_str = str(tracker_config)

    # ── Cache hit check ──────────────────────────────────────────────────────
    if _cache_is_valid(cache_path, video_path, model_name, conf, imgsz,
                       tracker_config_str, max_frames):
        logger.info("Cache hit — reusing %s", cache_path)
        with cache_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data["metadata"]

    # ── Load model ───────────────────────────────────────────────────────────
    model = _load_model(model_name, fallback_model)

    # ── Run tracking ─────────────────────────────────────────────────────────
    logger.info(
        "Running %s + ByteTrack on %s  (conf=%.2f imgsz=%d max_frames=%s)",
        model_name, video_path.name, conf, imgsz, max_frames,
    )
    records: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    t0 = time.perf_counter()

    results_gen = model.track(
        source=str(video_path),
        stream=True,        # frame-by-frame, low memory
        persist=True,       # keep track IDs across frames (required for ByteTrack)
        tracker=tracker_config_str,
        classes=None,       # Detect all object classes (persons, vehicles, items, pets)
        conf=conf,
        imgsz=imgsz,
        device=device,
        verbose=False,
    )

    for frame_number, result in enumerate(results_gen):
        if max_frames is not None and frame_number >= max_frames:
            break

        timestamp = frame_number / fps  # seconds from start

        boxes = result.boxes
        if boxes is not None and boxes.id is not None:
            ids   = boxes.id.int().cpu().tolist()
            xyxy  = boxes.xyxy.cpu().tolist()
            confs = boxes.conf.cpu().tolist()
            clss  = boxes.cls.int().cpu().tolist() if boxes.cls is not None else [0] * len(ids)
            names = getattr(result, 'names', None) or getattr(model, 'names', {}) or {}

            for track_id, (x1, y1, x2, y2), det_conf, cls_id in zip(ids, xyxy, confs, clss):
                seen_ids.add(track_id)
                x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
                bottom_center = [round((x1 + x2) / 2, 2), round(y2, 2)]
                raw_name = names.get(cls_id, "Person")
                cls_name = str(raw_name).capitalize()

                records.append({
                    "track_id": track_id,
                    "entity_id": f"{cls_name} #{track_id}",
                    "class_name": cls_name,
                    "frame_number": frame_number,
                    "timestamp_seconds": round(timestamp, 4),
                    "bounding_box": [round(x1, 2), round(y1, 2),
                                     round(x2, 2), round(y2, 2)],
                    "bottom_center": bottom_center,
                    "detection_confidence": round(float(det_conf), 4),
                })

        # Progress reporting every 30 frames
        if frame_number % 30 == 0:
            if progress_callback:
                progress_callback(frame_number, effective_total)
            elapsed = time.perf_counter() - t0
            fps_real = (frame_number + 1) / elapsed if elapsed > 0 else 0
            logger.debug("Frame %d/%d  %.1f FPS", frame_number, effective_total, fps_real)

    elapsed = time.perf_counter() - t0
    processing_fps = effective_total / elapsed if elapsed > 0 else 0

    metadata: dict[str, Any] = {
        "video_path": str(video_path),
        "fps": round(fps, 4),
        "width": width,
        "height": height,
        "frame_count": total_frames,
        "frames_processed": frame_number + 1,
        "model_name": model_name,
        "conf": conf,
        "imgsz": imgsz,
        "tracker_config": tracker_config_str,
        "device": device,
        "max_frames": max_frames,
        "total_raw_track_ids": len(seen_ids),
        "total_records": len(records),
        "processing_fps": round(processing_fps, 2),
        "processing_seconds": round(elapsed, 2),
        "cache_path": str(cache_path),
    }

    # ── Write cache ──────────────────────────────────────────────────────────
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_data = {"metadata": metadata, "records": records}
    with cache_path.open("w", encoding="utf-8") as f:
        json.dump(cache_data, f)

    logger.info(
        "Detection done: %d frames, %d unique IDs, %.1f FPS  -> %s",
        frame_number + 1, len(seen_ids), processing_fps, cache_path,
    )
    return metadata


def load_cache(cache_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load a previously saved track cache.  Returns (metadata, records)."""
    cache_path = Path(cache_path)
    if not cache_path.exists():
        raise FileNotFoundError(f"Track cache not found: {cache_path}")
    with cache_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data["metadata"], data["records"]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_model(model_name: str, fallback: str) -> YOLO:
    """Try to load *model_name*; fall back to *fallback* if unavailable."""
    # Check project root for the weight file first (avoids re-download)
    for name in (model_name, fallback):
        candidate = Path(name)
        # Also check project root
        root_candidate = Path(__file__).resolve().parents[4] / name
        if root_candidate.exists():
            candidate = root_candidate
        try:
            model = YOLO(str(candidate))
            logger.info("Loaded model: %s", name)
            return model
        except Exception as e:
            logger.warning("Could not load %s: %s", name, e)
    raise RuntimeError(
        f"Neither '{model_name}' nor '{fallback}' could be loaded. "
        "Ensure weight files are present in the project root or on PATH."
    )


def _cache_is_valid(
    cache_path: Path,
    video_path: Path,
    model_name: str,
    conf: float,
    imgsz: int,
    tracker_config: str,
    max_frames: int | None,
) -> bool:
    """Return True iff the cache exists and was produced with identical params."""
    if not cache_path.exists():
        return False
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        m = data["metadata"]
        return (
            Path(m["video_path"]).resolve() == Path(video_path).resolve()
            and m["model_name"] == model_name
            and abs(m["conf"] - conf) < 1e-6
            and m["imgsz"] == imgsz
            and m["tracker_config"] == tracker_config
            and m["max_frames"] == max_frames
        )
    except Exception:
        return False
