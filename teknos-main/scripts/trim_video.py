"""
trim_video.py — Trim a video clip to [start, end] seconds using imageio-ffmpeg.

Uses the bundled FFmpeg binary from imageio-ffmpeg (no system FFmpeg required).

Usage:
  python scripts/trim_video.py --video datasets/videos/avenue_test_01.avi --start 0 --end 15
  python scripts/trim_video.py --video datasets/videos/avenue_test_01.avi --start 10 --end 30 --out outputs/clip_10_30.mp4
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Trim a video clip using FFmpeg")
    p.add_argument("--video", required=True, type=Path)
    p.add_argument("--start", required=True, type=float, help="Start time (seconds)")
    p.add_argument("--end", required=True, type=float, help="End time (seconds)")
    p.add_argument("--out", type=Path, default=None,
                   help="Output path (default: outputs/trim_<start>_<end>.mp4)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    video_path = Path(args.video).resolve()

    if not video_path.exists():
        print(f"ERROR: video not found: {video_path}")
        sys.exit(1)

    duration = args.end - args.start
    if duration <= 0:
        print("ERROR: end must be greater than start")
        sys.exit(1)

    if args.out:
        out_path = Path(args.out)
    else:
        stem = video_path.stem
        out_path = video_path.parent.parent.parent / "outputs" / \
                   f"{stem}_trim_{int(args.start)}_{int(args.end)}.mp4"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg_exe,
        "-y",                         # overwrite output
        "-ss", str(args.start),       # seek to start (before -i for speed)
        "-i", str(video_path),
        "-t", str(duration),          # duration
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",                        # no audio
        str(out_path),
    ]

    print(f"Trimming {video_path.name}  [{args.start}s – {args.end}s]  -> {out_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg error:\n", result.stderr[-2000:])
        sys.exit(1)

    print(f"Done -> {out_path}  ({out_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
