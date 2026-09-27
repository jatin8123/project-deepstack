"""
test_models.py
--------------
These tests check Task's own behavior in isolation — no database, no
files. That's what "unit" testing means: testing one small unit of
logic on its own. Each function named test_* is a separate test case;
pytest runs each one and reports pass/fail individually.
"""

from datetime import date, timedelta
from models import Task


def test_new_task_has_no_completions():
    t = Task(name="Read", kind="habit")
    assert t.completed_dates == []
    assert t.current_streak() == 0


def test_mark_complete_adds_today():
    t = Task(name="Read", kind="habit")
    t.mark_complete()
    assert t.is_completed_today()
    assert t.current_streak() == 1


def test_mark_complete_is_idempotent():
    """Marking complete twice in one day shouldn't create two entries."""
    t = Task(name="Read", kind="habit")
    t.mark_complete()
    t.mark_complete()
    assert len(t.completed_dates) == 1


def test_streak_counts_consecutive_days():
    t = Task(name="Read", kind="habit")
    today = date.today()
    for i in range(3):
        t.mark_complete(today - timedelta(days=i))
    assert t.current_streak() == 3


def test_streak_breaks_on_gap():
    t = Task(name="Read", kind="habit")
    today = date.today()
    t.mark_complete(today)
    t.mark_complete(today - timedelta(days=2))  # day 1 is skipped -> gap
    assert t.current_streak() == 1
