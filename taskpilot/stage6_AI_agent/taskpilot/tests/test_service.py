"""
test_service.py
----------------
Phase 4 update: every service call now needs a user_id, since tasks
are scoped per-user. We create a real user via storage.create_user()
at the top of each test (bypassing the HTTP registration endpoint,
since these are logic-tier tests, not HTTP tests).
"""

import service
import storage
import auth
import ai


def make_user(username="alice"):
    hashed = auth.hash_password("testpassword")
    return storage.create_user(username, hashed)


def test_add_and_get_task():
    user = make_user()
    task = service.add_task(user["id"], "Buy milk", "task")
    all_tasks = service.get_all_tasks(user["id"])
    assert any(t.id == task.id and t.name == "Buy milk" for t in all_tasks)


def test_tasks_are_isolated_per_user():
    alice = make_user("alice")
    bob = make_user("bob")
    service.add_task(alice["id"], "Alice's task", "task")
    service.add_task(bob["id"], "Bob's task", "task")

    alice_tasks = service.get_all_tasks(alice["id"])
    bob_tasks = service.get_all_tasks(bob["id"])

    assert [t.name for t in alice_tasks] == ["Alice's task"]
    assert [t.name for t in bob_tasks] == ["Bob's task"]


def test_complete_task_marks_today():
    user = make_user()
    task = service.add_task(user["id"], "Meditate", "habit")
    completed = service.complete_task(user["id"], task.id)
    assert completed.is_completed_today()


def test_cannot_complete_another_users_task():
    alice = make_user("alice")
    bob = make_user("bob")
    task = service.add_task(alice["id"], "Alice's task", "task")
    result = service.complete_task(bob["id"], task.id)  # bob tries to complete alice's task
    assert result is None


def test_delete_task():
    user = make_user()
    task = service.add_task(user["id"], "Temp task", "task")
    assert service.delete_task(user["id"], task.id) is True
    assert service.delete_task(user["id"], task.id) is False


def test_weekly_completion_rate_no_tasks():
    user = make_user()
    assert service.weekly_completion_rate(user["id"]) == 0.0


def test_weekly_completion_rate_with_completion():
    user = make_user()
    task = service.add_task(user["id"], "Stretch", "habit")
    service.complete_task(user["id"], task.id)
    rate = service.weekly_completion_rate(user["id"])
    assert rate > 0


# ---- Phase 5: AI feature tests ----
# These mock ai.py itself, not the HTTP call inside it — we're testing
# that service.py correctly wires AI results into the real database,
# not re-testing ai.py's own logic (that's test_ai.py's job).

def test_categorize_task_persists_category(monkeypatch):
    monkeypatch.setattr(ai, "categorize_task", lambda name: "Health")
    user = make_user()
    task = service.add_task(user["id"], "Morning run", "habit")

    updated = service.categorize_task(user["id"], task.id)

    assert updated.category == "Health"
    # confirm it's really persisted, not just returned in-memory
    reloaded = service.get_all_tasks(user["id"])[0]
    assert reloaded.category == "Health"


def test_categorize_nonexistent_task_returns_none(monkeypatch):
    monkeypatch.setattr(ai, "categorize_task", lambda name: "Health")
    user = make_user()
    assert service.categorize_task(user["id"], 9999) is None


def test_cannot_categorize_another_users_task(monkeypatch):
    monkeypatch.setattr(ai, "categorize_task", lambda name: "Health")
    alice = make_user("alice")
    bob = make_user("bob")
    task = service.add_task(alice["id"], "Alice's task", "task")
    result = service.categorize_task(bob["id"], task.id)
    assert result is None


def test_get_weekly_summary_calls_ai_with_users_tasks(monkeypatch):
    captured = {}

    def fake_summary(tasks):
        captured["tasks"] = tasks
        return "Great week!"

    monkeypatch.setattr(ai, "weekly_summary", fake_summary)
    user = make_user()
    service.add_task(user["id"], "Read", "habit")

    result = service.get_weekly_summary(user["id"])

    assert result == "Great week!"
    assert len(captured["tasks"]) == 1
    assert captured["tasks"][0].name == "Read"
