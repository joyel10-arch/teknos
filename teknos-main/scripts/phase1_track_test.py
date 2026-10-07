"""
Phase 1: YOLO person detection + ByteTrack + annotated output video.
Run from the project root:  python scripts/phase1_track_test.py
"""
from collections import defaultdict, deque
from pathlib import Path
import time

import cv2
from ultralytics import YOLO

# ---------- Settings (edit these) ----------
VIDEO_PATH = Path("datasets/videos/avenue_test_01.avi")
OUTPUT_PATH = Path("outputs/phase1_annotated.mp4")
MODEL_NAME = "yolo11n.pt"   # fallback: "yolov8n.pt"
CONF_THRESHOLD = 0.30
IMAGE_SIZE = 640
TRAIL_LENGTH = 30
# -------------------------------------------


def format_time(seconds: float) -> str:
    """Return mm:ss.s, e.g. 00:04.1"""
    minutes = int(seconds // 60)
    return f"{minutes:02d}:{seconds - minutes * 60:04.1f}"


def main():
    if not VIDEO_PATH.exists():
        raise FileNotFoundError(f"Video not found: {VIDEO_PATH}")

    cap = cv2.VideoCapture(str(VIDEO_PATH))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    print(f"Video: {width}x{height}, {fps:.2f} FPS, {total_frames} frames")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(OUTPUT_PATH), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )

    model = YOLO(MODEL_NAME)  # downloads weights on first run
    results = model.track(
        source=str(VIDEO_PATH),
        stream=True,            # process frame by frame (low memory)
        persist=True,           # keep track IDs across frames
        tracker="bytetrack.yaml",
        classes=[0],            # COCO class 0 = person only
        conf=CONF_THRESHOLD,
        imgsz=IMAGE_SIZE,
        device="cpu",
        verbose=False,
    )

    trails = defaultdict(lambda: deque(maxlen=TRAIL_LENGTH))
    seen_ids = set()
    frames_per_id = defaultdict(int)
    start = time.time()

    for frame_number, result in enumerate(results):
        frame = result.orig_img.copy()
        timestamp = frame_number / fps  # timestamp = frame_number / fps

        boxes = result.boxes
        if boxes is not None and boxes.id is not None:
            ids = boxes.id.int().cpu().tolist()
            xyxy = boxes.xyxy.cpu().tolist()
            confs = boxes.conf.cpu().tolist()

            for track_id, (x1, y1, x2, y2), conf in zip(ids, xyxy, confs):
                seen_ids.add(track_id)
                frames_per_id[track_id] += 1
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                bottom_center = (int((x1 + x2) / 2), y2)
                trails[track_id].append(bottom_center)

                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 200, 0), 2)
                label = f"Person_{track_id} {conf:.2f}"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), (255, 200, 0), -1)
                cv2.putText(frame, label, (x1 + 2, y1 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

                # trajectory trail
                points = list(trails[track_id])
                for i in range(1, len(points)):
                    cv2.line(frame, points[i - 1], points[i], (0, 255, 255), 2)

        cv2.putText(frame, f"Time {format_time(timestamp)}", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        writer.write(frame)

        if frame_number % 30 == 0:
            print(f"Frame {frame_number}/{total_frames}  "
                  f"({time.time() - start:.1f}s elapsed)")

    writer.release()
    print(f"\nDone in {time.time() - start:.1f}s")
    print(f"Unique track IDs seen: {len(seen_ids)}")
    short = [i for i, n in frames_per_id.items() if n < 15]
    print(f"IDs lasting < 15 frames (likely flicker): {len(short)}")
    print("Longest 10 tracks (id, frames):",
        sorted(frames_per_id.items(), key=lambda x: -x[1])[:10])
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()