"""
service.py
----------
Phase 2 update: now calls storage's targeted DB functions instead of
bulk load/save. Notice the public functions here — add_task,
complete_task, delete_task, get_all_tasks, weekly_completion_rate —
kept the SAME NAMES AND SIGNATURES as Phase 1. That's exactly why
cli.py needed ZERO changes when we swapped the storage engine
underneath. This is the entire point of layering the app this way.
"""

from typing import List, Optional
from datetime import date, timedelta

from models import Task
import storage


def get_all_tasks() -> List[Task]:
    return storage.get_all_tasks()


def add_task(name: str, kind: str = "task") -> Task:
    return storage.insert_task(name, kind)


def complete_task(task_id: int) -> Optional[Task]:
    if storage.add_completion(task_id):
        return storage.get_task(task_id)
    return None


def delete_task(task_id: int) -> bool:
    return storage.delete_task(task_id)


def weekly_completion_rate() -> float:
    tasks = storage.get_all_tasks()
    if not tasks:
        return 0.0
    days = [date.today() - timedelta(days=i) for i in range(7)]
    total_slots = len(tasks) * len(days)
    completed_slots = sum(1 for t in tasks for d in days if d in t.completed_dates)
    return round(100 * completed_slots / total_slots, 1) if total_slots else 0.0
