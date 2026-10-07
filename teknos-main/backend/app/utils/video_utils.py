"""
video_utils.py — Lightweight video metadata helpers (no YOLO needed).
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import cv2


@dataclass
class VideoMeta:
    """Basic video properties read by OpenCV."""
    path: Path
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float
    original_name: str


def get_video_meta(path: Path) -> VideoMeta:
    """Read width, height, fps, frame_count from *path*.

    Raises ValueError if the file cannot be opened or has invalid properties.
    """
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"OpenCV cannot open video: {path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    if fps <= 0 or width <= 0 or height <= 0:
        raise ValueError(
            f"Invalid video properties (fps={fps}, {width}x{height}): {path}"
        )
    if frame_count <= 0:
        raise ValueError(f"Video has no frames: {path}")

    return VideoMeta(
        path=path,
        width=width,
        height=height,
        fps=round(fps, 4),
        frame_count=frame_count,
        duration_seconds=round(frame_count / fps, 4),
        original_name=path.name,
    )


def safe_filename(name: str) -> str:
    """Return a filename with only safe characters (alphanumeric, dash, underscore, dot)."""
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)
