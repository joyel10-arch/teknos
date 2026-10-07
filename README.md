<p align="center">
  <img src="https://img.shields.io/badge/TEKNOS-Autonomous_Vision-00d4ff?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiPjxjaXJjbGUgY3g9IjEyIiBjeT0iMTIiIHI9IjEwIi8+PGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iMyIvPjwvc3ZnPg==" alt="TeknOS Badge" />
  <img src="https://img.shields.io/badge/YOLOv11-Object_Detection-ff6b6b?style=for-the-badge" alt="YOLOv11" />
  <img src="https://img.shields.io/badge/ByteTrack-Multi_Object_Tracking-4ecdc4?style=for-the-badge" alt="ByteTrack" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-Frontend-61dafb?style=for-the-badge&logo=react&logoColor=black" alt="React" />
</p>

<h1 align="center">🔬 TeknOS — Autonomous Vision & Behaviour Intelligence</h1>

<p align="center">
  <strong>AI-powered surveillance analytics platform that detects, tracks, and classifies human behaviour in real-time video feeds.</strong>
</p>

<p align="center">
  Upload any video → YOLO object detection → ByteTrack multi-person tracking → Behaviour classification → Rich interactive dashboard
</p>

---

## 🎯 Overview

**TeknOS** is an end-to-end intelligent video analytics system that combines state-of-the-art computer vision with a modern, premium web interface. It processes surveillance footage to automatically detect objects, track individuals across frames, classify behaviours, and flag anomalies — all presented through an intuitive, real-time dashboard.

The system is designed for **security operations**, **warehouse monitoring**, **retail analytics**, and any scenario requiring automated visual intelligence.

---

## ✨ Key Features

### 🤖 AI & Computer Vision
- **YOLOv11 Object Detection** — Detects people, vehicles, bags, and other objects with high accuracy
- **ByteTrack Multi-Object Tracking** — Maintains persistent identity across frames with minimal ID switches
- **Behaviour Classification** — Automatically categorizes activities (walking, loitering, running, restricted zone entry)
- **Anomaly Detection** — Flags abnormal behaviours with configurable severity levels (high / medium / info)
- **Zone-Based Analysis** — Configurable virtual zones with directional flow enforcement

### 🖥️ Interactive Dashboard
- **Real-Time Video Analysis** — Canvas overlay with bounding boxes, trajectory paths, and tracking IDs
- **AI Reticle** — Dynamic targeting overlay that follows tracked objects
- **Behaviour Distribution Charts** — Donut and bar charts showing activity breakdown
- **Event Timeline** — Filterable audit log of all detected events with severity classification
- **Analytics Dashboard** — KPIs, zone risk assessment, model performance metrics
- **Render Settings** — Toggle bounding boxes, tracking IDs, trajectory paths, and confidence thresholds

### 🏗️ Architecture
- **Full-Stack Application** — React frontend + FastAPI backend
- **Modular Pipeline** — Pluggable detection, tracking, and analysis stages
- **Export-Ready Data** — JSON exports for tracks, events, zones, and summary metrics
- **Any Video Support** — Processes videos of any length and resolution

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 18, Vite, Recharts | Interactive UI, charts, video canvas |
| **Styling** | Custom CSS Design System | Premium dark theme with glassmorphism |
| **Backend** | FastAPI, Uvicorn | REST API, video upload, pipeline orchestration |
| **Detection** | YOLOv11 (Ultralytics) | Real-time object detection |
| **Tracking** | ByteTrack | Multi-object tracking with Kalman filtering |
| **Video** | OpenCV, FFmpeg | Frame extraction, video annotation |
| **Icons** | Lucide React | Modern icon set |

---

## 📂 Project Structure

```
teknos/
├── frontend/                    # React + Vite frontend application
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   │   ├── TrackingCanvas.jsx    # Video overlay with bounding boxes
│   │   │   ├── BehaviourChart.jsx    # Analytics charts (donut + bar)
│   │   │   ├── EventTimeline.jsx     # Filterable event audit log
│   │   │   ├── ActivityPanel.jsx     # Active tracks sidebar
│   │   │   ├── VideoAnalyzer.jsx     # Main video player component
│   │   │   └── UploadModal.jsx       # Video upload interface
│   │   ├── pages/               # Route pages
│   │   │   ├── Dashboard.jsx         # Main dashboard with KPIs
│   │   │   ├── VideoAnalysis.jsx     # Video analysis workspace
│   │   │   ├── Analytics.jsx         # Detailed analytics view
│   │   │   └── BehaviourEvents.jsx   # Event log with filters
│   │   ├── context/
│   │   │   └── DataContext.jsx       # Global state (tracks, events, summary)
│   │   └── data/
│   │       └── mockData.js           # Fallback demo data
│   ├── public/
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── teknos-main/                 # Backend + AI pipeline
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py              # FastAPI application & routes
│   │   │   ├── config.py            # Configuration & zone definitions
│   │   │   ├── services/
│   │   │   │   └── detector_tracker.py  # YOLO + ByteTrack pipeline
│   │   │   ├── models/              # Data models
│   │   │   └── utils/               # Helper utilities
│   │   ├── configs/                 # Zone & pipeline configuration
│   │   └── requirements.txt         # Python dependencies
│   ├── scripts/
│   │   ├── run_custom_video.py      # Main pipeline entry point
│   │   ├── run_full_pipeline.py     # Full analysis pipeline
│   │   ├── analyse_trajectories.py  # Trajectory analysis
│   │   └── export_for_frontend.py   # Data export utilities
│   ├── frontend/public/demo/        # Generated demo output files
│   │   ├── annotated.mp4            # AI-annotated video
│   │   ├── tracks.json              # Track data per frame
│   │   ├── events.json              # Detected events
│   │   ├── summary.json             # Pipeline summary metrics
│   │   └── zones.json               # Zone configurations
│   └── .gitignore
│
└── README.md                    # This file
```

---

## 🚀 Getting Started

### Prerequisites

| Requirement | Version |
|-------------|---------|
| **Python** | ≥ 3.10 |
| **Node.js** | ≥ 18.0 |
| **npm** | ≥ 9.0 |
| **FFmpeg** | Latest (for video processing) |
| **CUDA** (optional) | ≥ 11.8 (for GPU acceleration) |

### 1. Clone the Repository

```bash
git clone https://github.com/joyel10-arch/teknos.git
cd teknos
```

### 2. Backend Setup

```bash
cd teknos-main/backend

# Create a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd ../../frontend

# Install dependencies
npm install
```

### 4. Environment Configuration

```bash
# Backend — copy and configure
cp teknos-main/.env.example teknos-main/.env

# Frontend — copy and configure  
cp frontend/.env.example frontend/.env
```

### 5. Run the Application

**Terminal 1 — Backend (FastAPI):**
```bash
cd teknos-main/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend (Vite):**
```bash
cd frontend
npm run dev
```

**Open your browser** at `http://localhost:5173` 🎉

---

## 📖 Usage Guide

### Uploading & Analysing a Video

1. Click the **Upload** button in the top navigation bar
2. Select any video file (`.mp4`, `.avi`, `.mov`, etc.)
3. The backend processes the video through the AI pipeline:
   - **Stage 1:** YOLOv11 object detection + ByteTrack tracking
   - **Stage 2:** Track filtering & behaviour classification
   - **Stage 3:** Zone-based event analysis
   - **Stage 4:** Video annotation & data export
4. Once complete, the dashboard automatically loads the results

### Dashboard Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Overview KPIs, recent sessions, security alerts, zone risk assessment |
| **Video Analysis** | Interactive video player with canvas overlays, object log sidebar |
| **Analytics** | Behaviour distribution charts, event frequency histograms |
| **Behaviour Events** | Full event audit log with severity filtering |

### Render Settings (Video Analysis Page)

- **Bounding Boxes** — Toggle object detection rectangles
- **Tracking IDs** — Show/hide persistent ID labels
- **Trajectory Paths** — Display movement trails
- **AI Reticle** — Dynamic targeting overlay
- **Confidence Threshold** — Filter by detection confidence

---

## 🧠 AI Pipeline Details

```
Video Input
    │
    ▼
┌──────────────────────┐
│  YOLOv11 Detection   │  ← Detects objects per frame
│  (Ultralytics)       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  ByteTrack Tracker   │  ← Associates detections across frames
│  (Kalman + IoU)      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Track Filtering     │  ← Removes short/noisy tracks
│  & Classification    │  ← Labels behaviour (walk, loiter, run)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Zone Event Engine   │  ← Checks zone entry, direction, dwell time
│  (Configurable)      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Export & Annotate   │  ← Generates annotated video + JSON data
└──────────────────────┘
```

### Detected Event Types

| Event | Severity | Description |
|-------|----------|-------------|
| `normal_walkthrough` | Info | Standard transit through a zone |
| `loitering` | Medium | Stationary behaviour exceeding dwell threshold |
| `restricted_zone_entry` | High | Entry into a configured restricted area |
| `wrong_direction_movement` | Medium | Movement against configured directional flow |

---

## ⚙️ Configuration

### Zone Configuration (`backend/configs/zones.json`)

Define virtual zones with custom rules:

```json
{
  "zones": [
    {
      "zone_id": "entrance_gate",
      "zone_name": "Building Entrance",
      "type": "restricted",
      "polygon": [[x1,y1], [x2,y2], ...]
    },
    {
      "zone_id": "walkway",
      "zone_name": "Main Walkway",
      "type": "directional",
      "allowed_direction": "left_to_right"
    }
  ]
}
```

---

## 🧪 Running the Pipeline Manually

```bash
cd teknos-main

# Process a specific video file
python -m scripts.run_custom_video path/to/your/video.mp4

# Output will be generated in frontend/public/demo/
```

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/api/upload` | Upload video for processing |
| `GET` | `/api/demo/summary` | Get analysis summary |
| `GET` | `/api/demo/tracks` | Get tracking data |
| `GET` | `/api/demo/events` | Get detected events |
| `GET` | `/api/demo/zones` | Get zone configuration |
| `GET` | `/api/demo/video` | Stream annotated video |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [Ultralytics](https://github.com/ultralytics/ultralytics) — YOLOv11 object detection
- [ByteTrack](https://github.com/ifzhang/ByteTrack) — Multi-object tracking
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [React](https://react.dev/) — Frontend UI library
- [Vite](https://vitejs.dev/) — Next-generation frontend tooling
- [Recharts](https://recharts.org/) — Composable charting library
- [Lucide](https://lucide.dev/) — Beautiful open-source icons

---

<p align="center">
  <strong>Built with ❤️ for intelligent surveillance analytics</strong>
</p>
