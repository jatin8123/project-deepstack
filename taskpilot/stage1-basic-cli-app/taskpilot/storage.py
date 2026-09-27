"""
storage.py
----------
This file is the ONLY place that knows data is stored as JSON on disk.
Everything else in the app (cli.py) just calls load_tasks() / save_tasks()
without caring how or where the data actually lives.

Why this matters for later: in Phase 2, we swap JSON for SQLite. If your
storage logic were scattered through the app, that'd be a painful rewrite.
Because it's isolated here, we'll mostly just rewrite THIS file.
"""

import json
import itertools
from pathlib import Path
from typing import List

import models
from models import Task

DATA_FILE = Path(__file__).parent / "data" / "tasks.json"


def load_tasks() -> List[Task]:
    """Load all tasks from the JSON file. Returns an empty list if none exist yet."""
    if not DATA_FILE.exists():
        return []

    with open(DATA_FILE, "r") as f:
        raw = json.load(f)

    tasks = [Task.from_dict(item) for item in raw]

    # Make sure new tasks get IDs that don't collide with loaded ones.
    if tasks:
        max_id = max(t.id for t in tasks)
        models._id_counter = itertools.count(max_id + 1)

    return tasks


def save_tasks(tasks: List[Task]) -> None:
    """Write all tasks to the JSON file, overwriting whatever was there."""
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump([t.to_dict() for t in tasks], f, indent=2)
