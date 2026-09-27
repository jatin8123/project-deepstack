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
