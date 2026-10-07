import sys
from pathlib import Path
import json
import time
import shutil
import cv2
import numpy as np
import subprocess

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import settings
from app.services.detector_tracker import run_detection_and_tracking
from app.services.track_processor import process_tracks
from app.services.zone_engine import ZoneEngine, SceneConfig
from app.services.behaviour_engine import run_behaviour_engine, BehaviourEvent
from app.services.confidence import compute_all_confidences

def draw_tech_reticle(frame, bbox, tid, eid, action, conf, is_abnormal, speed=0.0):
    x1, y1, x2, y2 = [int(v) for v in bbox]
    h, w, _ = frame.shape
    
    # Bound check
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w - 1, x2), min(h - 1, y2)
    box_w = x2 - x1
    box_h = y2 - y1
    if box_w <= 0 or box_h <= 0:
        return

    # Color definitions (BGR)
    # Abnormal: Vibrant Red/Pink (BGR: 120, 80, 255)
    # Normal: Neon Cyan/Teal (BGR: 255, 215, 0)
    color = (120, 80, 255) if is_abnormal else (255, 215, 0)
    bg_color = (30, 20, 60) if is_abnormal else (30, 40, 20)

    # 1. Main bounding box line
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)

    # 2. Corner Reticles (L-shaped bracket caps on 4 corners)
    corner_len = min(14, max(4, int(min(box_w, box_h) * 0.2)))
    thick = 2
    # Top-Left
    cv2.line(frame, (x1, y1), (x1 + corner_len, y1), color, thick, cv2.LINE_AA)
    cv2.line(frame, (x1, y1), (x1, y1 + corner_len), color, thick, cv2.LINE_AA)
    # Top-Right
    cv2.line(frame, (x2, y1), (x2 - corner_len, y1), color, thick, cv2.LINE_AA)
    cv2.line(frame, (x2, y1), (x2, y1 + corner_len), color, thick, cv2.LINE_AA)
    # Bottom-Left
    cv2.line(frame, (x1, y2), (x1 + corner_len, y2), color, thick, cv2.LINE_AA)
    cv2.line(frame, (x1, y2), (x1, y2 - corner_len), color, thick, cv2.LINE_AA)
    # Bottom-Right
    cv2.line(frame, (x2, y2), (x2 - corner_len, y2), color, thick, cv2.LINE_AA)
    cv2.line(frame, (x2, y2), (x2, y2 - corner_len), color, thick, cv2.LINE_AA)

    # 3. Centroid Crosshair / Dot
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    cv2.circle(frame, (cx, cy), 3, color, -1, cv2.LINE_AA)
    if is_abnormal:
        cv2.circle(frame, (cx, cy), 8, color, 1, cv2.LINE_AA)

    # 4. Floating Header Badge (Top-Left above box)
    status_str = "ABNORMAL" if is_abnormal else "NORMAL"
    icon = "!! " if is_abnormal else ""
    conf_pct = int(conf * 100) if conf <= 1.0 else int(conf)
    label_text = f"{icon}{eid} • {action} ({conf_pct}%) [{status_str}]"
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.42
    font_thick = 1
    (t_w, t_h), baseline = cv2.getTextSize(label_text, font, font_scale, font_thick)
    
    pad = 4
    badge_y1 = max(0, y1 - t_h - pad * 2)
    badge_y2 = badge_y1 + t_h + pad * 2
    badge_x1 = x1
    badge_x2 = min(w - 1, badge_x1 + t_w + pad * 2)
    
    # Draw dark translucent badge background
    if badge_y2 > badge_y1 and badge_x2 > badge_x1:
        sub_img = frame[badge_y1:badge_y2, badge_x1:badge_x2]
        rect_img = np.full(sub_img.shape, bg_color, dtype=np.uint8)
        res = cv2.addWeighted(sub_img, 0.25, rect_img, 0.75, 1.0)
        frame[badge_y1:badge_y2, badge_x1:badge_x2] = res
        cv2.rectangle(frame, (badge_x1, badge_y1), (badge_x2, badge_y2), color, 1, cv2.LINE_AA)
        cv2.putText(frame, label_text, (badge_x1 + pad, badge_y2 - pad - 1), font, font_scale, (255, 255, 255), font_thick, cv2.LINE_AA)


def run_pipeline(video_file: Path):
    DEMO_DIR = settings.PROJECT_ROOT / "frontend" / "public" / "demo"
    CACHE_PATH = DEMO_DIR / "temp_cache.json"
    ZONE_PATH  = settings.PROJECT_ROOT / "datasets" / "zones" / "avenue_walkway_zones.json"
    
    if CACHE_PATH.exists():
        try:
            CACHE_PATH.unlink()
        except Exception:
            pass

    print("Stage 1: YOLO Object Detection + ByteTrack")
    meta = run_detection_and_tracking(video_file, CACHE_PATH, max_frames=None)
    
    print("Stage 2: Process Tracks")
    with CACHE_PATH.open() as f:
        cache = json.load(f)
    records = cache["records"]
    
    FPS = meta["fps"]
    WIDTH = meta["width"]
    HEIGHT = meta["height"]
    VIDEO_DURATION = meta["frames_processed"] / FPS
    
    tracks, summary = process_tracks(records, fps=FPS, min_track_seconds=0.5)
    
    print("Stage 3: Zones and Behaviour Engine")
    scene = SceneConfig.model_validate(json.loads(ZONE_PATH.read_text()))
    zone_engine = ZoneEngine(scene, actual_width=WIDTH, actual_height=HEIGHT)
    events = run_behaviour_engine(tracks, zone_engine, "uploaded", FPS, WIDTH, HEIGHT)
    compute_all_confidences(events)
    
    print("Stage 4: Rendering AI Reticle Annotated Video")
    ANNOTATED_MP4 = DEMO_DIR / "annotated.mp4"
    frame_events = {}
    tracks_by_id = {t.track_id: t for t in tracks}
    for evt in events:
        track = tracks_by_id.get(evt.track_id)
        if track:
            for fr in track.frames:
                if evt.start_time_seconds <= fr.timestamp_seconds <= evt.end_time_seconds:
                    frame_events.setdefault(fr.frame_number, []).append(evt)
                    
    frame_boxes = {}
    for t in tracks:
        if t.is_valid_track:
            for fr in t.frames:
                active_evts = [e for e in frame_events.get(fr.frame_number, []) if e.track_id == t.track_id]
                abnormal_evt = next((e for e in active_evts if e.severity in ['medium', 'high']), None)
                is_abnormal = abnormal_evt is not None
                
                if abnormal_evt:
                    action = abnormal_evt.event_type.replace('_', ' ').title()
                elif fr.speed_px_per_second > 100:
                    action = "Running"
                elif fr.speed_px_per_second > 12:
                    action = "Walking"
                elif fr.speed_px_per_second > 2:
                    action = "Standing"
                else:
                    action = "Stationary"

                frame_boxes.setdefault(fr.frame_number, []).append(
                    (t.track_id, t.entity_id, fr.bounding_box, action, fr.detection_confidence, is_abnormal, fr.speed_px_per_second)
                )

    cap = cv2.VideoCapture(str(video_file))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(ANNOTATED_MP4), fourcc, FPS, (WIDTH, HEIGHT))
    
    fn = 0
    while True:
        ret, frame = cap.read()
        if not ret or fn >= meta["frames_processed"]:
            break
        
        # draw reticles on detected objects
        for (tid, eid, bbox, action, conf, is_abnormal, speed) in frame_boxes.get(fn, []):
            draw_tech_reticle(frame, bbox, tid, eid, action, conf, is_abnormal, speed)
            
        out.write(frame)
        fn += 1
    
    cap.release()
    out.release()
    
    # Re-encode to web H.264
    try:
        H264_MP4 = DEMO_DIR / "annotated_h264.mp4"
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", str(ANNOTATED_MP4),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
            str(H264_MP4)
        ]
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if H264_MP4.exists():
            shutil.move(str(H264_MP4), str(ANNOTATED_MP4))
    except Exception as e:
        print("FFmpeg re-encoding warning:", e)
    
    print("Stage 5: Exporting JSON Analysis Data")
    def event_to_dict(e):
        return {
            "event_id": e.event_id, "entity_id": e.entity_id, "track_id": e.track_id,
            "event_type": e.event_type, "severity": e.severity, "start_time_seconds": e.start_time_seconds,
            "duration_seconds": e.duration_seconds, "zone_id": e.zone_id, "zone_name": e.zone_name,
            "confidence": e.confidence, "reason": e.reason,
        }
        
    events_export = sorted([event_to_dict(e) for e in events], key=lambda e: e["start_time_seconds"])
    (DEMO_DIR / "events.json").write_text(json.dumps(events_export, indent=2))
    
    tracks_export = []
    for t in sorted(tracks, key=lambda t: t.track_id):
        track_evts = [e for e in events if e.track_id == t.track_id]
        abnormal_evt = next((e for e in track_evts if e.severity in ['medium', 'high']), None)
        status = "Abnormal" if abnormal_evt else "Normal"
        
        speeds = [fr.speed_px_per_second for fr in t.frames if not fr.is_interpolated]
        avg_speed = float(np.mean(speeds)) if speeds else 0.0
        
        if abnormal_evt:
            behaviour = abnormal_evt.event_type.replace('_', ' ').title()
        elif avg_speed > 100:
            behaviour = "Running"
        elif avg_speed > 12:
            behaviour = "Walking"
        elif avg_speed > 2:
            behaviour = "Standing"
        else:
            behaviour = "Stationary"

        trajectory = []
        for fr in t.frames:
            trajectory.append({
                "t": round(fr.timestamp_seconds, 2),
                "x": round(fr.smoothed_center[0], 1),
                "y": round(fr.smoothed_center[1], 1),
                "bbox": [round(v, 1) for v in fr.bounding_box]
            })

        tracks_export.append({
            "track_id": t.track_id,
            "entity_id": t.entity_id,
            "is_valid_track": t.is_valid_track,
            "duration_seconds": t.duration_seconds,
            "mean_detection_confidence": t.mean_detection_confidence,
            "net_dx": round(avg_speed, 1),
            "status": status,
            "behaviour": behaviour,
            "dwell": f"{t.duration_seconds:.1f}s",
            "trajectory": trajectory
        })
    (DEMO_DIR / "tracks.json").write_text(json.dumps(tracks_export, indent=2))
    
    # Build complete severity breakdown
    severity_counts = {}
    type_counts = {}
    for e in events:
        sev = e.severity
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        etype = e.event_type
        type_counts[etype] = type_counts.get(etype, 0) + 1

    summary_dict = {
        "video_id": "uploaded", "duration_seconds": VIDEO_DURATION, "fps": FPS,
        "resolution": {"width": WIDTH, "height": HEIGHT},
        "valid_tracked_persons": summary["valid_tracked_persons"],
        "raw_track_ids": summary["raw_track_ids"],
        "total_events": len(events),
        "event_counts_by_severity": severity_counts,
        "event_counts_by_type": type_counts,
        "processing_info": {"model_name": "YOLOv11", "processing_fps": meta["processing_fps"]}
    }
    (DEMO_DIR / "summary.json").write_text(json.dumps(summary_dict, indent=2))
    
    zone_export = json.loads(ZONE_PATH.read_text())
    (DEMO_DIR / "zones.json").write_text(json.dumps(zone_export, indent=2))

if __name__ == "__main__":
    run_pipeline(Path(sys.argv[1]))
