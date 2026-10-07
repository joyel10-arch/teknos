"""
analyse_trajectories.py — Read the cached tracks, print trajectory statistics,
and produce trajectory_overview.png + reference frame PNG.
"""
from __future__ import annotations
import json, sys
import numpy as np
import cv2
from pathlib import Path
from collections import defaultdict

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.track_processor import process_tracks

CACHE = Path("backend/outputs/tracks_cache/avenue_test_01__yolo11n_pt__conf25__imgsz640__maxfall_tracks.json")
VIDEO = Path("datasets/videos/avenue_test_01.avi")
OUT_DIR = Path("outputs")
OUT_DIR.mkdir(exist_ok=True)

with open(CACHE) as f:
    d = json.load(f)
meta = d["metadata"]
records = d["records"]

tracks, summary = process_tracks(
    records, fps=meta["fps"],
    min_track_seconds=1.0, max_gap_seconds=1.0, smoothing_window_seconds=0.4
)

print(f"raw={summary['raw_track_ids']}  valid={summary['valid_tracked_persons']}  short={summary['short_tracks_filtered']}")

valid_tracks = [t for t in tracks if t.is_valid_track]
xs_all, ys_all = [], []
for t in valid_tracks:
    xs_all += [fr.bottom_center[0] for fr in t.frames]
    ys_all += [fr.bottom_center[1] for fr in t.frames]

y_arr = np.array(ys_all)
x_arr = np.array(xs_all)
print(f"X: {x_arr.min():.0f} - {x_arr.max():.0f}")
print(f"Y: {y_arr.min():.0f} - {y_arr.max():.0f}")
for pct in [10, 25, 50, 75, 90]:
    print(f"  y p{pct}: {np.percentile(y_arr, pct):.0f}")

print("\n--- Valid tracks by duration (top 40) ---")
valid_sorted = sorted(valid_tracks, key=lambda t: -t.duration_seconds)
for t in valid_sorted[:40]:
    xs = [fr.bottom_center[0] for fr in t.frames]
    ys = [fr.bottom_center[1] for fr in t.frames]
    dx = xs[-1] - xs[0]
    ymean = sum(ys) / len(ys)
    print(
        f"  id={t.track_id:3d}  dur={t.duration_seconds:5.1f}s"
        f"  x={min(xs):.0f}-{max(xs):.0f}"
        f"  y={min(ys):.0f}-{max(ys):.0f}"
        f"  ymean={ymean:.0f}"
        f"  dx={dx:+.0f}"
    )

# ── Extract reference frame (frame 100) ──────────────────────────────────────
cap = cv2.VideoCapture(str(VIDEO))
cap.set(cv2.CAP_PROP_POS_FRAMES, 100)
ret, ref_frame = cap.read()
cap.release()
if ret:
    ref_path = OUT_DIR / "reference_frame.png"
    cv2.imwrite(str(ref_path), ref_frame)
    print(f"\nReference frame saved: {ref_path}")
else:
    ref_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    print("WARNING: Could not read reference frame")

# ── Trajectory overview ───────────────────────────────────────────────────────
W, H = meta["width"], meta["height"]
overview = ref_frame.copy() if ret else np.zeros((H, W, 3), dtype=np.uint8)
# Darken background to see trails better
overview = (overview * 0.4).astype(np.uint8)

colours = [
    (0, 255, 255), (0, 200, 255), (180, 255, 0), (255, 100, 0),
    (200, 0, 255), (0, 255, 128), (255, 0, 128), (128, 255, 0),
]

for i, t in enumerate(valid_tracks):
    pts = [(int(fr.bottom_center[0]), int(fr.bottom_center[1])) for fr in t.frames]
    col = colours[i % len(colours)]
    for j in range(1, len(pts)):
        cv2.line(overview, pts[j - 1], pts[j], col, 1)
    # start dot
    cv2.circle(overview, pts[0], 4, (0, 255, 0), -1)
    # end dot
    cv2.circle(overview, pts[-1], 4, (0, 0, 255), -1)

cv2.putText(overview, f"Trajectory overview — {summary['valid_tracked_persons']} valid tracks",
            (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

overview_path = OUT_DIR / "trajectory_overview.png"
cv2.imwrite(str(overview_path), overview)
print(f"Trajectory overview saved: {overview_path}")
