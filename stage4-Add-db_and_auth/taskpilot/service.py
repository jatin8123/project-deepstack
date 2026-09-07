"""
service.py
----------
Phase 4 update: every function now takes a user_id and passes it down
to storage.py, so all task operations are scoped to whoever is logged
in. The function NAMES are still the same as Phase 1 — add_task,
complete_task, delete_task, get_all_tasks, weekly_completion_rate —
only the parameter list grew. cli.py and api.py both had to be updated
to pass a user_id in, but the shape of this layer stayed familiar.
"""

from typing import List, Optional
from datetime import date, timedelta

from models import Task
import storage


def get_all_tasks(user_id: int) -> List[Task]:
    return storage.get_all_tasks(user_id)


def add_task(user_id: int, name: str, kind: str = "task") -> Task:
    return storage.insert_task(user_id, name, kind)


def complete_task(user_id: int, task_id: int) -> Optional[Task]:
    if storage.add_completion(task_id, user_id):
        return storage.get_task(task_id, user_id)
    return None


def delete_task(user_id: int, task_id: int) -> bool:
    return storage.delete_task(task_id, user_id)


def weekly_completion_rate(user_id: int) -> float:
    tasks = storage.get_all_tasks(user_id)
    if not tasks:
        return 0.0
    days = [date.today() - timedelta(days=i) for i in range(7)]
    total_slots = len(tasks) * len(days)
    completed_slots = sum(1 for t in tasks for d in days if d in t.completed_dates)
    return round(100 * completed_slots / total_slots, 1) if total_slots else 0.0
