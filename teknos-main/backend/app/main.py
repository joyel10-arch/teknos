"""
main.py -- Read-only FastAPI serving SafeWatch AI demo outputs.

Endpoints:
  GET /api/health            -- liveness check
  GET /api/summary           -- summary.json
  GET /api/events            -- events.json (sorted by start_time_seconds)
  GET /api/tracks            -- tracks.json
  GET /api/zones             -- zones.json
  GET /api/video             -- annotated.mp4 (streams the file)
  GET /api/evidence/{id}     -- evidence/<id>.jpg

CORS is open for http://localhost:5173 (Vite dev server).

No upload, no database, no live inference.
"""
from __future__ import annotations

import json
from pathlib import Path

import sys

from fastapi import FastAPI, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import subprocess

# Resolve project root via settings so the path is correct regardless of CWD
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.config import settings  # noqa: E402 (after sys.path patch)

# -- Demo data directory (populated by run_full_pipeline.py / export_for_frontend.py)
DEMO_DIR = settings.PROJECT_ROOT / "frontend" / "public" / "demo"

app = FastAPI(
    title="SafeWatch AI Demo API",
    description=(
        "Read-only API that serves pre-computed trajectory analysis results. "
        "No live inference. No upload. No database."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# -- Helpers ------------------------------------------------------------------

def _load_json(filename: str) -> dict | list:
    """Load a JSON file from DEMO_DIR; raise 503 if missing."""
    path = DEMO_DIR / filename
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"{filename} not found in demo directory. Run the pipeline first.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


# -- Routes -------------------------------------------------------------------

@app.get("/api/health", tags=["meta"])
def health() -> dict:
    """Liveness check. Returns ok plus whether demo data is present."""
    return {
        "status": "ok",
        "demo_data_ready": (DEMO_DIR / "summary.json").exists(),
        "demo_dir": str(DEMO_DIR),
    }


@app.get("/api/summary", tags=["data"])
def get_summary() -> JSONResponse:
    """Video metadata, track counts, event counts by type, processing info, disclaimer."""
    return JSONResponse(_load_json("summary.json"))


@app.get("/api/events", tags=["data"])
def get_events() -> JSONResponse:
    """All behaviour events sorted by start_time_seconds."""
    return JSONResponse(_load_json("events.json"))


@app.get("/api/tracks", tags=["data"])
def get_tracks() -> JSONResponse:
    """Per-entity track summary rows (all tracks, valid and invalid)."""
    return JSONResponse(_load_json("tracks.json"))


@app.get("/api/zones", tags=["data"])
def get_zones() -> JSONResponse:
    """Zone configuration used for this analysis."""
    return JSONResponse(_load_json("zones.json"))


@app.get("/api/video", tags=["media"])
def get_video() -> FileResponse:
    """Stream the annotated MP4 video."""
    path = DEMO_DIR / "annotated.mp4"
    if not path.exists():
        raise HTTPException(status_code=503, detail="annotated.mp4 not found")
    return FileResponse(str(path), media_type="video/mp4",
                        filename="annotated.mp4")

@app.get("/api/raw_video", tags=["media"])
def get_raw_video() -> FileResponse:
    """Stream the raw unannotated MP4 video."""
    path = DEMO_DIR / "uploaded_input.mp4"
    if not path.exists():
        path = DEMO_DIR / "avenue_test_01.mp4"
    if not path.exists():
        path = settings.PROJECT_ROOT / "datasets" / "videos" / "avenue_test_01.avi"
    if not path.exists():
        raise HTTPException(status_code=404, detail="raw video not found")
    return FileResponse(str(path), media_type="video/mp4")


@app.get("/api/evidence/{event_id}", tags=["media"])
def get_evidence(event_id: str) -> FileResponse:
    """Return the evidence JPEG for a given event_id (e.g. evt_001)."""
    # Sanitise: allow only alphanumeric + underscore to prevent path traversal
    if not event_id.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid event_id format")
    path = DEMO_DIR / "evidence" / f"{event_id}.jpg"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No evidence frame for {event_id}")
    return FileResponse(str(path), media_type="image/jpeg")

@app.post("/api/upload", tags=["media"])
async def upload_video(file: UploadFile = File(...)):
    """Upload a video and run the pipeline."""
    video_path = DEMO_DIR / "uploaded_input.mp4"
    with open(video_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(file.file, buffer)
        
    script_path = settings.PROJECT_ROOT / "scripts" / "run_custom_video.py"
    
    # Run the custom pipeline script synchronously (wait for it to finish)
    subprocess.run(["python", str(script_path), str(video_path)], check=True, cwd=str(settings.PROJECT_ROOT))
    
    return {"message": "Pipeline finished successfully!"}
