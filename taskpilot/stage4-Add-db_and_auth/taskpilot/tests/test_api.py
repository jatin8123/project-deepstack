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
