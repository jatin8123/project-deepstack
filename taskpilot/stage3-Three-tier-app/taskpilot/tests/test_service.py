"""
test_service.py
----------------
These are closer to "integration" tests — they exercise service.py
talking to a real (temporary) SQLite database, end to end. This is
where we catch bugs that only show up when the pieces work together,
not just individually.
"""

import service


def test_add_and_get_task():
    task = service.add_task("Buy milk", "task")
    all_tasks = service.get_all_tasks()
    assert any(t.id == task.id and t.name == "Buy milk" for t in all_tasks)


def test_complete_task_marks_today():
    task = service.add_task("Meditate", "habit")
    completed = service.complete_task(task.id)
    assert completed.is_completed_today()


def test_complete_nonexistent_task_returns_none():
    assert service.complete_task(9999) is None


def test_delete_task():
    task = service.add_task("Temp task", "task")
    assert service.delete_task(task.id) is True
    assert service.delete_task(task.id) is False  # already gone, nothing to delete


def test_weekly_completion_rate_no_tasks():
    assert service.weekly_completion_rate() == 0.0


def test_weekly_completion_rate_with_completion():
    task = service.add_task("Stretch", "habit")
    service.complete_task(task.id)
    rate = service.weekly_completion_rate()
    assert rate > 0
