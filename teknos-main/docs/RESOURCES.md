# SafeWatch AI — External Resources & Licence Notes

> **Purpose**: This file lists every external component, dataset, and model used
> by SafeWatch AI, with licence information, how it is used, and any constraints
> that apply. Keeping this file accurate is required for responsible-claims compliance
> (Section 15 of the master prompt).

---

## 1. Computer-Vision / ML

### YOLO11n (Ultralytics)
- **Version**: weights shipped with `ultralytics==8.4.174`, model name `yolo11n.pt`
- **Licence**: [AGPL-3.0](https://github.com/ultralytics/ultralytics/blob/main/LICENSE)
  - ⚠️ **AGPL-3.0 requires that any network-distributed software using Ultralytics models
    must also be open-sourced under AGPL-3.0** unless a commercial licence is obtained
    from Ultralytics.  For this academic hackathon project (HackNex internal qualifier)
    the AGPL terms are satisfied by keeping the code in a non-commercially distributed
    repository.  If this project is ever deployed as a service, obtain a commercial
    licence or open-source the entire service under AGPL-3.0.
- **How used**: Person detection only (COCO class 0).  Outputs bounding boxes +
  detection confidence per frame.  No fine-tuning was performed.
- **Fallback**: `yolov8n.pt` (same licence, Ultralytics).

### ByteTrack (via Ultralytics tracking mode)
- **Paper**: ByteTrack: Multi-Object Tracking by Associating Every Detection Box
  (Zhang et al., ECCV 2022, arXiv:2110.06864)
- **Licence**: MIT (original ByteTrack repo);  the Ultralytics implementation is
  under AGPL-3.0 (bundled with ultralytics).
- **How used**: Assigns stable track IDs across frames.  Custom config at
  `backend/configs/bytetrack_custom.yaml`.

---

## 2. Core Libraries

| Library | Version | Licence | How used |
|---|---|---|---|
| **OpenCV** (`opencv-python`) | 5.0.0.93 | Apache-2.0 | Frame read, polygon test, drawing, VideoWriter |
| **NumPy** | 2.5.3 | BSD-3-Clause | Array maths, smoothing, trajectory computation |
| **PyTorch** | 2.14.1+cpu | BSD-style (Facebook) | YOLO inference backend (CPU only) |
| **FastAPI** | 0.142.2 | MIT | REST API framework |
| **Uvicorn** | 0.54.0 | BSD-3-Clause | ASGI server |
| **Pydantic** | 2.13.5 | MIT | Request/response validation, schema models |
| **pydantic-settings** | 2.15.0 | MIT | Config loading from .env |
| **python-multipart** | 0.0.32 | Apache-2.0 | File upload parsing |
| **imageio-ffmpeg** | 0.6.0 | BSD-2-Clause | Bundles a static FFmpeg binary for H.264 re-encoding |
| **pytest** | 9.1.1 | MIT | Test framework |
| **httpx** | 0.28.1 | BSD-3-Clause | FastAPI `TestClient` |
| **PyYAML** | 6.0.3 | MIT | Tracker YAML config loading |
| **python-dotenv** | 1.2.4 | BSD-3-Clause | .env file loading |

---

## 3. Dataset

### CUHK Avenue Dataset
- **Source**: Computer Vision Lab, The Chinese University of Hong Kong.
  http://www.cse.cuhk.edu.hk/leojia/projects/detectabnormal/dataset.html
- **Licence / Terms**: **Academic research use only**.  Redistribution or commercial
  use is not permitted.  This dataset must not be included in any public repository
  or shared outside the team.
- **Content**: Fixed-camera video of a campus walkway.  Contains staged anomalies
  (running, throwing objects, wrong-direction walking, a bag left on the ground).
  The "loitering" label in Avenue refers to a BAG LEFT ON GRASS, not a standing
  person — our loitering rule is therefore tested with synthetic tracks.
- **Files used**: `datasets/videos/avenue_test_01.avi` (640×360, 1439 frames,
  ~57.6 s).  Full dataset is at `Avenue_Dataset/` (git-ignored).

---

## 4. FFmpeg (via imageio-ffmpeg)
- **Version**: bundled static binary via `imageio-ffmpeg==0.6.0`
- **Licence**: LGPL-2.1+ / GPL-2+ depending on compile options.
  The `imageio-ffmpeg` distribution includes an LGPL build.
  See https://imageio.readthedocs.io/en/stable/reference/imageio_ffmpeg.html
- **How used**: Re-encodes OpenCV `mp4v` output to H.264 (`libx264`, `yuv420p`)
  for browser compatibility.

---

## 5. Responsible Use Constraints (summary)

1. **Anonymous tracking only** — no face recognition, no identity lookup.
2. **Decision support** — all outputs require human review; no automated enforcement.
3. **Not a classifier of intent** — events are labelled as rule deviations, never
   as criminal or suspicious behaviour.
4. **Pixel speed ≠ real-world speed** — no camera calibration is performed.
5. **Accuracy limitations**: performance degrades with occlusion, crowds, low light,
   low resolution, camera motion, similar clothing, and ID fragmentation.
6. All reported metrics must come from real runs (no fabricated numbers).
