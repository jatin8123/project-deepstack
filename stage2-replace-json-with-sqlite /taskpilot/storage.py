"""
storage.py
----------
Phase 2 update: swapped JSON-file storage for a real relational database
(SQLite, built into Python — no install needed). The functions this
module exposes are now targeted operations (insert one, get one, delete
one) rather than Phase 1's bulk load/save — that's how real databases
are meant to be used.

Schema (two tables, related by a foreign key):
  tasks       (id, name, kind, created_on)
  completions (id, task_id -> tasks.id, completed_date)

This is called "normalization": instead of cramming a list of dates into
one column, completions get their own table, each row pointing back to
its task via task_id. Same pattern you'd use designing any relational
schema.
"""

import sqlite3
from pathlib import Path
from datetime import date
from typing import List, Optional

from models import Task

DB_PATH = Path(__file__).parent / "data" / "taskpilot.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist yet. Safe to call every startup."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                created_on TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                completed_date TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        """)


def _row_to_task(row, completion_dates) -> Task:
    task = Task(name=row[1], kind=row[2], id=row[0])
    task.created_on = date.fromisoformat(row[3])
    task.completed_dates = [date.fromisoformat(d) for d in completion_dates]
    return task


def get_all_tasks() -> List[Task]:
    with _connect() as conn:
        task_rows = conn.execute("SELECT id, name, kind, created_on FROM tasks").fetchall()
        tasks = []
        for row in task_rows:
            comp_rows = conn.execute(
                "SELECT completed_date FROM completions WHERE task_id = ?", (row[0],)
            ).fetchall()
            tasks.append(_row_to_task(row, [c[0] for c in comp_rows]))
        return tasks


def get_task(task_id: int) -> Optional[Task]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, name, kind, created_on FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if not row:
            return None
        comp_rows = conn.execute(
            "SELECT completed_date FROM completions WHERE task_id = ?", (task_id,)
        ).fetchall()
        return _row_to_task(row, [c[0] for c in comp_rows])


def insert_task(name: str, kind: str) -> Task:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (name, kind, created_on) VALUES (?, ?, ?)",
            (name, kind, date.today().isoformat()),
        )
        new_id = cursor.lastrowid
    return get_task(new_id)


def add_completion(task_id: int, on: date = None) -> bool:
    """Returns False if the task doesn't exist, True otherwise (even if already completed today)."""
    on = on or date.today()
    with _connect() as conn:
        exists = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not exists:
            return False
        already = conn.execute(
            "SELECT id FROM completions WHERE task_id = ? AND completed_date = ?",
            (task_id, on.isoformat()),
        ).fetchone()
        if not already:
            conn.execute(
                "INSERT INTO completions (task_id, completed_date) VALUES (?, ?)",
                (task_id, on.isoformat()),
            )
    return True


def delete_task(task_id: int) -> bool:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0
