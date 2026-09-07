"""
test_api.py
-----------
Phase 4 update: tests now go through the full auth flow — register,
log in to get a token, then send that token on every subsequent
request, exactly like the real frontend does. We also test that
requests WITHOUT a token are correctly rejected, and that one user
can't see another's tasks over the API.
"""

from fastapi.testclient import TestClient
from api import app
import service


def register_and_login(client, username="alice", password="testpassword"):
    client.post("/api/register", json={"username": username, "password": password})
    resp = client.post("/api/token", data={"username": username, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_creates_user():
    with TestClient(app) as client:
        resp = client.post("/api/register", json={"username": "alice", "password": "testpassword"})
        assert resp.status_code == 201
        assert resp.json()["username"] == "alice"


def test_cannot_register_duplicate_username():
    with TestClient(app) as client:
        client.post("/api/register", json={"username": "alice", "password": "testpassword"})
        resp = client.post("/api/register", json={"username": "alice", "password": "other"})
        assert resp.status_code == 400


def test_login_with_wrong_password_fails():
    with TestClient(app) as client:
        client.post("/api/register", json={"username": "alice", "password": "testpassword"})
        resp = client.post("/api/token", data={"username": "alice", "password": "wrong"})
        assert resp.status_code == 401


def test_tasks_require_auth():
    with TestClient(app) as client:
        resp = client.get("/api/tasks")  # no Authorization header
        assert resp.status_code == 401


def test_create_and_list_task_with_auth():
    with TestClient(app) as client:
        headers = register_and_login(client)
        resp = client.post("/api/tasks", json={"name": "Read a book", "kind": "habit"}, headers=headers)
        assert resp.status_code == 201

        resp = client.get("/api/tasks", headers=headers)
        assert resp.status_code == 200
        assert any(t["name"] == "Read a book" for t in resp.json())


def test_users_cannot_see_each_others_tasks():
    with TestClient(app) as client:
        alice_headers = register_and_login(client, "alice", "pass1")
        bob_headers = register_and_login(client, "bob", "pass2")

        client.post("/api/tasks", json={"name": "Alice task"}, headers=alice_headers)

        bob_tasks = client.get("/api/tasks", headers=bob_headers).json()
        assert bob_tasks == []


def test_complete_nonexistent_task_returns_404():
    with TestClient(app) as client:
        headers = register_and_login(client)
        resp = client.post("/api/tasks/9999/complete", headers=headers)
        assert resp.status_code == 404


def test_delete_task():
    with TestClient(app) as client:
        headers = register_and_login(client)
        created = client.post("/api/tasks", json={"name": "Temp"}, headers=headers).json()
        resp = client.delete(f"/api/tasks/{created['id']}", headers=headers)
        assert resp.status_code == 204


def test_stats_endpoint_requires_auth():
    with TestClient(app) as client:
        resp = client.get("/api/stats")
        assert resp.status_code == 401


# ---- Phase 5: AI route tests ----
# We mock service.ai's functions here too, at the HTTP layer, so these
# tests verify routing/auth/serialization, not the LLM call itself.

def test_suggest_task_requires_auth():
    with TestClient(app) as client:
        resp = client.post("/api/tasks/suggest", json={"text": "meditate daily"})
        assert resp.status_code == 401


def test_suggest_task_returns_structured_result(monkeypatch):
    monkeypatch.setattr(
        service.ai, "parse_natural_language_task",
        lambda text: {"name": "Meditate", "kind": "habit"},
    )
    with TestClient(app) as client:
        headers = register_and_login(client)
        resp = client.post("/api/tasks/suggest", json={"text": "meditate daily"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"name": "Meditate", "kind": "habit"}


def test_categorize_task_endpoint(monkeypatch):
    monkeypatch.setattr(service.ai, "categorize_task", lambda name: "Health")
    with TestClient(app) as client:
        headers = register_and_login(client)
        created = client.post("/api/tasks", json={"name": "Morning run", "kind": "habit"}, headers=headers).json()

        resp = client.post(f"/api/tasks/{created['id']}/categorize", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["category"] == "Health"


def test_summary_endpoint(monkeypatch):
    monkeypatch.setattr(service.ai, "weekly_summary", lambda tasks: "You're doing great!")
    with TestClient(app) as client:
        headers = register_and_login(client)
        resp = client.get("/api/summary", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["summary"] == "You're doing great!"


def test_ai_routes_return_503_when_api_key_missing(monkeypatch):
    import ai as ai_module

    def raise_config_error(text):
        raise ai_module.AIConfigError("ANTHROPIC_API_KEY is not set.")

    monkeypatch.setattr(service.ai, "parse_natural_language_task", raise_config_error)
    with TestClient(app) as client:
        headers = register_and_login(client)
        resp = client.post("/api/tasks/suggest", json={"text": "anything"}, headers=headers)
        assert resp.status_code == 503
