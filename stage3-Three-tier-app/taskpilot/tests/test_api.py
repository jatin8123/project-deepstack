"""
test_api.py
-----------
These test the HTTP layer itself — sending real HTTP requests (in
process, no actual network) into the FastAPI app and checking the JSON
responses and status codes. This is the presentation-tier equivalent
of what test_service.py did for the logic tier.

TestClient triggers FastAPI's startup event (storage.init_db()) when
used as a context manager, so each test gets its DB properly initialized
against the temporary DB path set up by conftest.py's autouse fixture.
"""

from fastapi.testclient import TestClient
from api import app


def test_create_and_list_task():
    with TestClient(app) as client:
        resp = client.post("/api/tasks", json={"name": "Read a book", "kind": "habit"})
        assert resp.status_code == 201
        created = resp.json()
        assert created["name"] == "Read a book"

        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        assert any(t["id"] == created["id"] for t in resp.json())


def test_complete_task():
    with TestClient(app) as client:
        created = client.post("/api/tasks", json={"name": "Stretch", "kind": "habit"}).json()
        resp = client.post(f"/api/tasks/{created['id']}/complete")
        assert resp.status_code == 200
        assert resp.json()["completed_today"] is True


def test_complete_nonexistent_task_returns_404():
    with TestClient(app) as client:
        resp = client.post("/api/tasks/9999/complete")
        assert resp.status_code == 404


def test_delete_task():
    with TestClient(app) as client:
        created = client.post("/api/tasks", json={"name": "Temp"}).json()
        resp = client.delete(f"/api/tasks/{created['id']}")
        assert resp.status_code == 204
        resp = client.delete(f"/api/tasks/{created['id']}")  # already gone
        assert resp.status_code == 404


def test_stats_endpoint():
    with TestClient(app) as client:
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        assert "weekly_completion_rate" in resp.json()
