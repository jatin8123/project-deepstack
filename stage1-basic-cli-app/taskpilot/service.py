"""
service.py
----------
This is the "business logic" layer — the rules of the app, independent of
how the user interacts with it. Right now only cli.py calls these
functions. In Phase 3, a web UI will call these EXACT SAME functions.
That's the whole point of a 3-tier design: the logic tier doesn't care
who's asking.

Notice this file imports storage.py, but cli.py (next file) will NOT
import storage.py directly — it only talks to service.py. That one rule
is what keeps the layers separated.
"""

from typing import List, Optional
from models import Task
import storage


def get_all_tasks() -> List[Task]:
    return storage.load_tasks()


def add_task(name: str, kind: str = "task") -> Task:
    tasks = storage.load_tasks()
    task = Task(name=name, kind=kind)
    tasks.append(task)
    storage.save_tasks(tasks)
    return task


def complete_task(task_id: int) -> Optional[Task]:
    tasks = storage.load_tasks()
    for t in tasks:
        if t.id == task_id:
            t.mark_complete()
            storage.save_tasks(tasks)
            return t
    return None


def delete_task(task_id: int) -> bool:
    tasks = storage.load_tasks()
    remaining = [t for t in tasks if t.id != task_id]
    if len(remaining) == len(tasks):
        return False  # nothing was deleted
    storage.save_tasks(remaining)
    return True


def weekly_completion_rate() -> float:
    """
    Rough stat: of all (task, day) slots over the last 7 days,
    what fraction got marked complete? Simple but gives a real signal.
    """
    from datetime import date, timedelta

    tasks = storage.load_tasks()
    if not tasks:
        return 0.0

    days = [date.today() - timedelta(days=i) for i in range(7)]
    total_slots = len(tasks) * len(days)
    completed_slots = sum(
        1 for t in tasks for d in days if d in t.completed_dates
    )
    return round(100 * completed_slots / total_slots, 1) if total_slots else 0.0
