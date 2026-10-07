# SafeWatch AI — Viva / Exam Preparation Notes

Plain-language explanations of every module, the design decisions made, and
the **known limitations** the viva examiner is likely to ask about.

---

## 1. What SafeWatch AI Does (30-second pitch)

SafeWatch AI analyses a surveillance video offline.  It:
1. Detects every person in every frame with a pre-trained YOLO model.
2. Links detections across frames into continuous trajectories using a
   tracker (ByteTrack).
3. Checks each trajectory against zone polygons and four behaviour rules.
4. Outputs a list of timestamped events (e.g., "Person_7 entered the
   restricted zone at 00:23.4").

It does **NOT** recognise faces, make intent or threat claims, or use any
live camera stream.  All outputs use anonymous IDs.

---

## 2. Phase B0 — Scaffolding

| File | What it does |
|------|--------------|
| `config.py` | Single source of truth for all thresholds and paths.  Loaded via `pydantic-settings` so every value can be overridden from a `.env` file without touching code. |
| `bytetrack_custom.yaml` | Tuned tracker settings (lower match and new-track thresholds) to reduce fragmentation on the CUHK Avenue footage. |
| `requirements.txt` | Pinned dependency list, reproducible across machines. |
| `.gitignore` | Excludes the virtual environment, model weights, raw datasets, and `.env` secrets from version control. |
| `RESOURCES.md` | Lists every third-party library and its licence.  YOLO11 is AGPL-3.0 — flagged because AGPL requires open-sourcing any network service built on it. |

---

## 3. Phase B1 — Detection & Tracking (`detector_tracker.py`)

**How it works**:
`YOLO.track()` runs both detection and tracking in one call.  For each frame
it returns bounding boxes, confidence scores, and a persistent integer
`track_id` assigned by ByteTrack.

**Why YOLO11n (nano)?**
Fastest variant.  On CPU at 640 px it achieves ~5-8 FPS on the test clip,
which is acceptable for offline analysis.  Larger models would be more
accurate but too slow on CPU.

**Why ByteTrack?**
ByteTrack maintains tracks for low-confidence detections (those "bytes"
between the high/low thresholds).  This reduces track fragmentation at
partial occlusions better than simpler IoU-only matching.

**What the cache is**:
After the first run, all per-frame track records are serialised to a JSON
file.  Subsequent pipeline runs load from cache (< 1 s) instead of
re-running YOLO (> 3 min).  Cache keys encode the model, confidence,
and image size so a changed config invalidates the cache.

**Experiment results (real run, 400 frames)**:

| Config | Unique IDs | Short tracks (<15 f) | FPS |
|--------|------------|----------------------|-----|
| A: default YAML, 640 px | 48 | 17 | 4.6 |
| B: custom YAML, 640 px  | 30 |  8 | 5.7 |  <- chosen
| C: default YAML, 960 px | 41 | 15 | 4.0 |
| D: custom YAML, 960 px  | 30 |  6 | 3.8 |

Config B was chosen: the custom tracker YAML reduces fragmentation by **37.5%**
(48 to 30 unique IDs; (48 - 30) / 48 = 0.375) and runs the fastest.
Config D matched the ID count but was slower due to the larger inference size.

> **Correction note**: an earlier summary incorrectly stated "60% reduction".
> The correct figure is (48 - 30) / 48 = 37.5%.

---

## 4. Phase B1 — Track Processing (`track_processor.py`)

**Gap filling**: if a person disappears for <= `MAX_GAP_SECONDS` (config
default 1.0 s, spec default 1.0 s) the missing positions are linearly
interpolated.  Interpolated frames are flagged and excluded from
detection-confidence averaging.

**Smoothing**: a centred moving-average window (`SMOOTHING_WINDOW_SECONDS =
0.4 s`) is applied to bottom-centre positions before speed is computed.
This reduces the effect of YOLO bounding-box jitter (+-3-5 px at 640x360).

**Validity filter**: tracks with fewer observed (non-interpolated) frames than
`MIN_TRACK_SECONDS x FPS` (config default 1.0 s x FPS, spec default 1.0 s)
are marked `is_valid_track = False`.  Invalid tracks are **never** passed to
the behaviour engine, so they generate zero events.

**Speed metric -- net displacement (not path length)**:
For each frame, speed is computed as the Euclidean distance between the
smoothed position at frame `i - 2` and frame `i + 2`, divided by the elapsed
time (4-frame window at the given FPS).  This is "net displacement" speed.

---

## 5. Phase B1/B2 -- Zone Engine (`zone_engine.py`)

**Zone types**: `allowed`, `monitored`, `restricted`, `directional`.

**Point-in-polygon**: uses OpenCV's `pointPolygonTest` (ray-casting), which
handles concave polygons correctly.  A bounding-box pre-filter avoids
running the full test for points obviously outside the polygon.

**Hysteresis**: a simple counter-based state machine per (track_id, zone_id)
pair.  The person must be inside for `ZONE_MIN_FRAMES` consecutive frames
before the membership is "confirmed".  This prevents zone-boundary oscillation
from generating phantom entry/exit events.

---

## 6. Phase B1/B2 -- Behaviour Engine (`behaviour_engine.py`)

Four required behaviour rules (Section 8 of master prompt):

| # | Event type | Severity | Trigger |
|---|------------|----------|---------|
| 1 | `normal_walkthrough` | info | Sustained movement (>= `MIN_WALK_SECONDS`) through an allowed zone.  Only fires if the track has **no** medium/high events. |
| 2 | `restricted_zone_entry` | high | First outside-to-inside crossing of a restricted zone.  Fires **once per entry**; cooldown prevents re-firing within `RESTRICTED_REENTRY_COOLDOWN_SECONDS`. |
| 3 | `loitering` | medium | Dwell in a monitored zone for >= `LOITERING_DURATION_SECONDS` with mean speed <= `MAX_AVERAGE_SPEED_PX_PER_SECOND`. |
| 4 | `wrong_direction_movement` | medium | Accumulated reverse-axis travel in a directional zone exceeds `MIN_DIRECTION_TRAVEL_PX`. |

**Optional extras (NOT part of the required spec)**:
`abnormal_speed` and `sudden_motion_cessation` are listed in `config.py` with
`ENABLE_ABNORMAL_SPEED_RULE = False` and `ENABLE_SUDDEN_CESSATION_RULE = False`
by default.  They are never instantiated in the default pipeline and are
**not counted** in any output statistics.

---

## 7. Evidence Confidence (`confidence.py`)

```
C = 0.45 x D + 0.30 x T + 0.25 x R
```

| Component | Meaning |
|-----------|---------|
| D - Detection | Mean YOLO detection confidence over the relevant frames |
| T - Track stability | Ratio of real (non-interpolated) frames to total frames |
| R - Rule margin | How strongly the observation exceeded the rule threshold |

All components are in [0, 1].  C is clipped to [0, 1].

---

## 8. Known Limitations

> These are real limitations you must be able to explain in a viva.

### 8.1 Net-displacement speed can miss back-and-forth movement

The speed metric measures the straight-line distance between the smoothed
position a few frames before and a few frames after the current frame.

If a person paces back and forth over a short distance (e.g., +-40 px around
a fixed point), each short segment of travel looks like low displacement.
The net-displacement speed may stay near zero even though the person is
physically active.

**Effect**: such a person may incorrectly trigger a `loitering` event (because
their measured speed is low) even though they are not truly stationary.

**Alternative**: path-length speed (summing all frame-to-frame displacements)
would detect back-and-forth movement better, but it inflates speed for
genuinely stationary persons due to YOLO box jitter (+-3-5 px per frame).

> We chose net displacement because false loitering is less harmful than
> missed loitering in a surveillance context, and jitter-robustness was
> the priority at 640 x 360 resolution.

---

### 8.2 ID switches after occlusion still exist

ByteTrack assigns a new integer `track_id` when a person is fully occluded
(e.g., walking behind a concrete column) and cannot be re-associated with
confidence.

**Effect**: one real person may appear as several separate `TrackData` objects
with different `entity_id` values.  Each fragment is independently checked
against the rules.

- Short fragments (< `MIN_TRACK_SECONDS`) are filtered out.
- Longer fragments near a zone boundary may fire **duplicate or partial events**
  for the same physical person.

The summary statistics (`raw_track_ids` vs `valid_tracked_persons`) report
how many raw IDs were generated vs how many survived the short-track filter,
giving an indication of fragmentation severity.

**Fix (out of scope for this project)**: a Re-ID (re-identification) module
that extracts appearance embeddings and links fragments across the occlusion.

---

### 8.3 `COUNT_INITIAL_INSIDE_AS_ENTRY = False` (documented limitation)

If a track is **first observed already inside** a restricted zone (e.g., the
person entered before the video starts, or before the tracker started tracking
them), no `restricted_zone_entry` event is fired.

This is intentional (`COUNT_INITIAL_INSIDE_AS_ENTRY` defaults to `False`)
because there is no evidence of an actual outside-to-inside crossing.  Firing
an event without a crossing would be a false positive.

**Effect**: some legitimate intrusions may be missed if the person was not
detected until they were already inside.

---

### 8.4 No real-world distance calibration

All speed thresholds are in **pixels per second at reference resolution
(640 x 360)**, not metres per second.  The pixel-to-metre conversion requires
camera calibration (focal length, tilt angle, mounting height) which is not
performed.

At runtime, pixel thresholds are scaled proportionally to the actual
resolution, but remain camera-specific.  The same threshold may flag a
person as "loitering" at one camera placement and not at another.

---

### 8.5 Offline / batch processing only

The pipeline processes a complete video file.  There is no live-stream
support, WebSocket feed, or frame-by-frame API.  Real-time adaptation
(e.g., sub-second latency alert) is out of scope.

---

## 9. Quick Glossary

| Term | Meaning in this project |
|------|------------------------|
| `entity_id` | Anonymous label: `"Person_<track_id>"`.  No face recognition. |
| `is_valid_track` | `True` if the track has enough observed frames to be reliable. |
| `bottom_center` | The midpoint of the bottom edge of the bounding box -- the point closest to the ground plane. |
| `smoothed_center` | Bottom-centre after moving-average smoothing, used for speed and direction. |
| `hysteresis` | Requiring N consecutive frames of agreement before changing the zone-membership state.  Prevents flicker at boundaries. |
| `net displacement` | Straight-line distance from start to end of a rolling window.  Used for speed. |
| `AGPL-3.0` | Ultralytics licence: any network service using YOLOv8/11 must open-source its code (or purchase a commercial licence). |
