"""
test_api.py -- TestClient tests for the read-only FastAPI demo API.

Tests:
  - GET /api/health returns 200 with status=ok
  - GET /api/summary returns 200 with required snake_case keys
  - GET /api/events returns 200 with a list, each event has required keys
  - GET /api/tracks returns 200 with a list
  - GET /api/zones returns 200 with zones list
  - GET /api/evidence/evt_001 returns 200 with image/jpeg
  - GET /api/evidence/<invalid> returns 400
  - GET /api/evidence/<nonexistent> returns 404

These tests run against the actual exported demo data, so they serve as
integration tests confirming pipeline outputs are well-formed.
"""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.main import app

client = TestClient(app)


# -- /api/health --------------------------------------------------------------

def test_health_returns_200():
    r = client.get("/api/health")
    assert r.status_code == 200


def test_health_body_has_status_ok():
    r = client.get("/api/health")
    assert r.json()["status"] == "ok"


def test_health_reports_demo_data_ready():
    r = client.get("/api/health")
    assert r.json()["demo_data_ready"] is True, (
        "demo_data_ready is False -- run scripts/run_full_pipeline.py first"
    )


# -- /api/summary -------------------------------------------------------------

REQUIRED_SUMMARY_KEYS = {
    "video_id", "duration_seconds", "fps", "resolution",
    "raw_track_ids", "valid_tracked_persons", "short_tracks_filtered",
    "event_counts_by_type", "event_counts_by_severity",
    "total_events", "processing_info", "disclaimer",
}

def test_summary_returns_200():
    assert client.get("/api/summary").status_code == 200


def test_summary_has_required_keys():
    body = client.get("/api/summary").json()
    missing = REQUIRED_SUMMARY_KEYS - set(body.keys())
    assert not missing, f"summary.json missing keys: {missing}"


def test_summary_counts_match_total():
    body = client.get("/api/summary").json()
    counts_sum = sum(body["event_counts_by_type"].values())
    assert counts_sum == body["total_events"], (
        f"sum of event_counts_by_type ({counts_sum}) != total_events ({body['total_events']})"
    )


def test_summary_resolution_has_width_and_height():
    body = client.get("/api/summary").json()
    res = body["resolution"]
    assert "width" in res and "height" in res


# -- /api/events --------------------------------------------------------------

REQUIRED_EVENT_KEYS = {
    "event_id", "video_id", "entity_id", "track_id",
    "event_type", "severity", "start_time_seconds", "end_time_seconds",
    "zone_id", "zone_name", "confidence", "reason",
}

def test_events_returns_200():
    assert client.get("/api/events").status_code == 200


def test_events_is_a_list():
    body = client.get("/api/events").json()
    assert isinstance(body, list)


def test_events_not_empty():
    body = client.get("/api/events").json()
    assert len(body) > 0, "No events returned -- pipeline may not have run"


def test_events_each_has_required_keys():
    body = client.get("/api/events").json()
    for evt in body:
        missing = REQUIRED_EVENT_KEYS - set(evt.keys())
        assert not missing, f"Event {evt.get('event_id')} missing keys: {missing}"


def test_events_sorted_by_start_time():
    body = client.get("/api/events").json()
    times = [e["start_time_seconds"] for e in body]
    assert times == sorted(times), "Events are not sorted by start_time_seconds"


def test_events_severity_values_are_valid():
    body = client.get("/api/events").json()
    valid = {"info", "medium", "high"}
    for evt in body:
        assert evt["severity"] in valid, f"Unexpected severity: {evt['severity']}"


# -- /api/tracks --------------------------------------------------------------

def test_tracks_returns_200():
    assert client.get("/api/tracks").status_code == 200


def test_tracks_is_a_list():
    assert isinstance(client.get("/api/tracks").json(), list)


def test_tracks_each_has_entity_id_and_duration():
    body = client.get("/api/tracks").json()
    for t in body:
        assert "entity_id" in t
        assert "duration_seconds" in t


# -- /api/zones ---------------------------------------------------------------

def test_zones_returns_200():
    assert client.get("/api/zones").status_code == 200


def test_zones_has_zones_list():
    body = client.get("/api/zones").json()
    assert "zones" in body
    assert isinstance(body["zones"], list)
    assert len(body["zones"]) >= 1


def test_zones_have_required_fields():
    body = client.get("/api/zones").json()
    for z in body["zones"]:
        assert "id" in z
        assert "type" in z
        assert "polygon" in z


# -- /api/evidence ------------------------------------------------------------

def test_evidence_evt_001_returns_jpeg():
    r = client.get("/api/evidence/evt_001")
    assert r.status_code == 200
    assert "image/jpeg" in r.headers["content-type"]


def test_evidence_invalid_id_returns_400():
    # ID contains a slash character that would not be URL-encoded by the test client;
    # use an id with a dot (not alphanumeric/underscore) so it fails the sanitise check.
    r = client.get("/api/evidence/evt.bad!")
    assert r.status_code == 400


def test_evidence_nonexistent_id_returns_404():
    r = client.get("/api/evidence/evt_9999")
    assert r.status_code == 404


# -- /api/video ---------------------------------------------------------------

def test_video_returns_200_or_streams():
    r = client.get("/api/video")
    assert r.status_code == 200
    assert "video/mp4" in r.headers.get("content-type", "")
