"""
config.py — SafeWatch AI single source of truth for all settings.

WHAT: Centralises every configurable value — paths, thresholds, limits — into one
      Pydantic-settings model loaded from environment variables / .env file.
WHY:  Avoids magic numbers scattered across modules; makes threshold tuning safe
      (change one place, all rules update); lets tests override values trivially.

Pixel-threshold scaling note (required reading):
  All pixel-distance thresholds in the behaviour rules (speed, min travel, etc.)
  are defined for a REFERENCE frame height of 360 px (the CUHK Avenue clip size).
  At runtime each threshold is multiplied by  (frame_height / 360)
  and horizontal thresholds by (frame_width / 640) so that the rules are
  approximately resolution-independent.  Real-world distances are NOT available
  without camera calibration; all "speed" values are in px/s at reference resolution.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """All configurable knobs for SafeWatch AI backend.

    Attribute names match the .env keys (case-insensitive).
    Values here are the documented defaults; override via .env or environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Paths (relative to project root E:\safewatch, resolved at runtime)
    # ------------------------------------------------------------------
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]  # E:\safewatch

    # Input locations
    VIDEOS_DIR: Path = Field(default=Path("datasets/videos"))
    ZONES_DIR: Path = Field(default=Path("datasets/zones"))
    GROUND_TRUTH_DIR: Path = Field(default=Path("datasets/ground_truth"))

    # Backend upload + output locations
    UPLOADS_DIR: Path = Field(default=Path("backend/uploads"))
    OUTPUTS_BASE: Path = Field(default=Path("backend/outputs"))
    TRACKS_CACHE_DIR: Path = Field(default=Path("backend/outputs/tracks_cache"))
    ANNOTATED_VIDEOS_DIR: Path = Field(default=Path("backend/outputs/annotated_videos"))
    EVIDENCE_FRAMES_DIR: Path = Field(default=Path("backend/outputs/evidence_frames"))
    REPORTS_DIR: Path = Field(default=Path("backend/outputs/reports"))
    DB_PATH: Path = Field(default=Path("backend/outputs/safewatch.db"))

    # ------------------------------------------------------------------
    # Model / tracker
    # ------------------------------------------------------------------
    YOLO_MODEL: str = Field(default="yolo11n.pt")
    YOLO_FALLBACK_MODEL: str = Field(default="yolov8n.pt")
    YOLO_CONF: float = Field(default=0.25, description="Detection confidence threshold")
    YOLO_IMGSZ: int = Field(default=640, description="Inference image size (px)")
    TRACKER_CONFIG: Path = Field(default=Path("backend/configs/bytetrack_custom.yaml"))
    DEVICE: str = Field(default="cpu")

    # ------------------------------------------------------------------
    # Track quality (Section 6)
    # ------------------------------------------------------------------
    MIN_TRACK_SECONDS: float = Field(
        default=1.0,
        description=(
            "Tracks shorter than this are marked invalid and produce no events. "
            "Spec default: 1.0 s.  At 25 FPS this means tracks with fewer than 25 "
            "observed detections are silently discarded."
        )
    )
    MAX_GAP_SECONDS: float = Field(
        default=1.0,
        description=(
            "Missing-frame gaps shorter than this are filled by linear interpolation. "
            "Spec default: 1.0 s.  Gaps wider than this are left as jumps in the track."
        )
    )
    SMOOTHING_WINDOW_SECONDS: float = Field(
        default=0.4,
        description="Moving-average window for bottom-centre smoothing (approx 0.4 s)"
    )

    # ------------------------------------------------------------------
    # Zone engine (Section 7 / 8)
    # ------------------------------------------------------------------
    ZONE_MIN_FRAMES: int = Field(
        default=3,
        description="Hysteresis: consecutive frames required before zone state changes"
    )

    # ------------------------------------------------------------------
    # Behaviour rules — thresholds defined at REFERENCE resolution 640x360
    # All pixel thresholds MUST be scaled by (frame_h / 360) or (frame_w / 640)
    # before use in the behaviour engine. See zone_engine.py / behaviour_engine.py.
    # ------------------------------------------------------------------
    REFERENCE_HEIGHT: int = Field(default=360, description="Reference frame height (px)")
    REFERENCE_WIDTH: int = Field(default=640, description="Reference frame width (px)")

    # Rule 1 — normal walkthrough
    MIN_WALK_SECONDS: float = Field(
        default=1.5,
        description="Min time traversing an allowed zone to emit a walkthrough event (s)"
    )

    # Rule 2 — restricted zone entry
    RESTRICTED_REENTRY_COOLDOWN_SECONDS: float = Field(
        default=2.0,
        description="After leaving restricted zone, min gap before re-triggering entry"
    )
    COUNT_INITIAL_INSIDE_AS_ENTRY: bool = Field(
        default=False,
        description="If False, tracks already inside restricted zone at first valid frame"
                    " do not fire an entry event (documented limitation)"
    )

    # Rule 3 — loitering
    LOITERING_DURATION_SECONDS: float = Field(
        default=10.0,
        description="Dwell in monitored zone required to flag loitering (s)"
    )
    MOVEMENT_WINDOW_SECONDS: float = Field(
        default=3.0,
        description="Rolling window for computing average speed in loitering check (s)"
    )
    MAX_AVERAGE_SPEED_PX_PER_SECOND: float = Field(
        default=8.0,
        description="Max pixel speed (at ref 640x360) to count as 'low-movement' (px/s)"
    )

    # Rule 4 — wrong direction movement
    MIN_DIRECTION_TRAVEL_PX: float = Field(
        default=80.0,
        description="Min reverse-axis travel (px at ref 640x360) to flag wrong direction"
    )

    # ------------------------------------------------------------------
    # Optional extra rules — NOT part of the required spec (Section 8).
    # Both are disabled by default and are NEVER counted in the default
    # pipeline output.  Enable only for experimental / exploratory use.
    # ------------------------------------------------------------------
    ENABLE_ABNORMAL_SPEED_RULE: bool = Field(
        default=False,
        description=(
            "extra (not part of the required spec) — enables the abnormal-speed rule "
            "(running / sprinting beyond a velocity threshold).  Disabled by default."
        )
    )
    ABNORMAL_SPEED_THRESHOLD_PX_PER_S: float = Field(
        default=120.0,
        description=(
            "extra (not part of the required spec) — speed threshold (px/s at ref "
            "640x360) above which a track is flagged as moving abnormally fast.  "
            "Only used when ENABLE_ABNORMAL_SPEED_RULE=True."
        )
    )
    ENABLE_SUDDEN_CESSATION_RULE: bool = Field(
        default=False,
        description=(
            "extra (not part of the required spec) — enables the sudden-motion-cessation "
            "rule (rapid deceleration from sustained motion to near-zero velocity).  "
            "Disabled by default."
        )
    )
    CESSATION_MIN_SPEED_PX_PER_S: float = Field(
        default=40.0,
        description=(
            "extra (not part of the required spec) — minimum sustained speed (px/s at ref "
            "640x360) before a sudden stop can be flagged.  Only used when "
            "ENABLE_SUDDEN_CESSATION_RULE=True."
        )
    )

    # ------------------------------------------------------------------
    # Evidence confidence (Section 9): C = 0.45*D + 0.30*T + 0.25*R
    # ------------------------------------------------------------------
    CONFIDENCE_W_DETECTION: float = Field(default=0.45)
    CONFIDENCE_W_TRACK: float = Field(default=0.30)
    CONFIDENCE_W_RULE: float = Field(default=0.25)

    # Evidence: how many frames after restricted entry to check for confirmation
    RESTRICTED_CONFIRM_FRAMES: int = Field(
        default=10,
        description="N frames after restricted entry to measure R (rule-evidence strength)"
    )

    # ------------------------------------------------------------------
    # Video pipeline
    # ------------------------------------------------------------------
    MAX_UPLOAD_SIZE_BYTES: int = Field(
        default=200 * 1024 * 1024,
        description="Maximum uploaded video size (bytes). Default 200 MB."
    )
    ALLOWED_EXTENSIONS: list[str] = Field(default=[".mp4", ".avi"])
    TRAJECTORY_TAIL_FRAMES: int = Field(
        default=30,
        description="Number of past bottom-centre points to draw as trajectory tail"
    )

    # Evidence frame JPEG quality (0-100)
    EVIDENCE_JPEG_QUALITY: int = Field(default=90)

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    APP_VERSION: str = Field(default="0.1.0")
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:5173"])
    API_PREFIX: str = Field(default="/api")

    def resolve(self, rel: Path) -> Path:
        """Return an absolute path from a project-root-relative path."""
        if rel.is_absolute():
            return rel
        return self.PROJECT_ROOT / rel


# Singleton — import this everywhere:  from app.config import settings
settings = Settings()
