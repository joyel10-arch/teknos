"""
extract_frame.py — Save a specific frame from a video as a PNG image.

Usage:
  python scripts/extract_frame.py --video datasets/videos/avenue_test_01.avi --frame 0
  python scripts/extract_frame.py --video datasets/videos/avenue_test_01.avi --time 5.0
  python scripts/extract_frame.py --video datasets/videos/avenue_test_01.avi --frame 0 --out outputs/frame_0.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

# Add backend to path so config is available
BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))
from app.config import settings


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract a single frame from a video as PNG")
    p.add_argument("--video", required=True, type=Path, help="Input video path")
    p.add_argument("--frame", type=int, default=None,
                   help="Frame number (0-indexed). Mutually exclusive with --time.")
    p.add_argument("--time", type=float, default=None,
                   help="Timestamp in seconds. Mutually exclusive with --frame.")
    p.add_argument("--out", type=Path, default=None,
                   help="Output PNG path. Defaults to outputs/frame_<N>.png")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    video_path = Path(args.video)
    if not video_path.is_absolute():
        video_path = settings.PROJECT_ROOT / video_path

    if not video_path.exists():
        print(f"ERROR: video not found: {video_path}")
        sys.exit(1)

    if args.frame is None and args.time is None:
        print("ERROR: specify --frame or --time")
        sys.exit(1)

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Resolve frame number
    if args.time is not None:
        frame_num = int(args.time * fps)
    else:
        frame_num = args.frame

    frame_num = max(0, min(frame_num, total - 1))

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print(f"ERROR: could not read frame {frame_num}")
        sys.exit(1)

    # Output path
    if args.out:
        out_path = Path(args.out)
    else:
        out_path = settings.PROJECT_ROOT / "outputs" / f"frame_{frame_num}.png"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), frame)
    print(f"Saved frame {frame_num} ({frame_num/fps:.2f}s) -> {out_path}")


if __name__ == "__main__":
    main()
