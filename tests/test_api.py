# tests/test_api.py
# Fix #29 — API endpoint and job store coverage

import pytest
import time
import uuid
from fastapi.testclient import TestClient

from unittest.mock import patch

@pytest.fixture
def store(tmp_path):
    from job_store import JobStore
    db_file = tmp_path / "test_jobs.db"
    return JobStore(db_path=str(db_file))


@pytest.fixture(scope="module", autouse=True)
def mock_pipeline():
    with patch("api_server.run_pipeline") as m1, \
         patch("api_server.resume_pipeline") as m2, \
         patch("api_server.run_localization_task") as m3:
        yield (m1, m2, m3)


# ── Job store tests ────────────────────────────────────────────────────────

def test_job_store_create_and_get(store):
    job_id = str(uuid.uuid4())
    store.create(job_id, {"status": "starting", "current_node": "init"})
    job = store.get(job_id)
    assert job is not None
    assert job["status"] == "starting"
    assert job["current_node"] == "init"


def test_job_store_update(store):
    job_id = str(uuid.uuid4())
    store.create(job_id, {"status": "starting", "current_node": "init"})
    store.update(job_id, {"status": "running", "current_node": "write"})
    job = store.get(job_id)
    assert job["status"] == "running"
    assert job["current_node"] == "write"


def test_job_store_update_data_blob(store):
    job_id = str(uuid.uuid4())
    store.create(job_id, {"status": "starting"})
    store.update(job_id, {"data": {"raw_blog": "hello world"}})
    job = store.get(job_id)
    assert job["data"]["raw_blog"] == "hello world"


def test_job_store_delete(store):
    job_id = str(uuid.uuid4())
    store.create(job_id, {"status": "starting"})
    store.delete(job_id)
    assert store.get(job_id) is None


def test_job_store_unknown_job_returns_none(store):
    assert store.get("nonexistent-id") is None


def test_job_store_cleanup(store):
    job_id = str(uuid.uuid4())
    store.create(job_id, {"status": "completed"})
    # Force the start_time into the past
    with store._connect() as conn:
        conn.execute(
            "UPDATE jobs SET start_time = ? WHERE job_id = ?",
            (time.time() - 99999, job_id)
        )
        conn.commit()
    removed = store.cleanup()
    assert removed >= 1
    assert store.get(job_id) is None


# ── API endpoint tests ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from api_server import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_root_redirect(client):
    res = client.get("/", follow_redirects=False)
    assert res.status_code == 307
    assert res.headers["location"] == "/app"


def test_generate_missing_topic(client):
    """Blank topic should fail validation — not trigger a paid pipeline run."""
    res = client.post("/api/generate", json={"topic": "hi", "mode": "news"})
    # "hi" is 2 chars, min_length is 5 — should return 422
    assert res.status_code == 422


def test_generate_invalid_mode(client):
    res = client.post("/api/generate", json={"topic": "AI in healthcare", "mode": "invalid"})
    assert res.status_code == 422


def test_generate_creates_job(client):
    res = client.post("/api/generate", json={
        "topic": "AI in healthcare 2025",
        "mode":  "news",
    })
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    assert data["status"] == "started"


def test_status_not_found(client):
    res = client.get("/api/status/nonexistent-job-id")
    assert res.status_code == 404


def test_status_returns_job(client):
    # Create a job first
    res = client.post("/api/generate", json={
        "topic": "Test topic for status check",
        "mode":  "news",
    })
    job_id = res.json()["job_id"]

    status_res = client.get(f"/api/status/{job_id}")
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["job_id"] == job_id
    assert "status" in data
    assert "current_node" in data


def test_feedback_not_found(client):
    res = client.post("/api/feedback", json={
        "job_id": "nonexistent",
        "action": "approve",
    })
    assert res.status_code == 404


def test_feedback_invalid_action(client):
    res = client.post("/api/feedback", json={
        "job_id": "some-id",
        "action": "delete",   # not in enum
    })
    assert res.status_code == 422
