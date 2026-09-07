"""
storage.py
----------
Phase 4 update: swapped SQLite for PostgreSQL, and added real
multi-user support. Two schema changes from Phase 2:

1. New `users` table.
2. `tasks` now has a `user_id` column (a foreign key to users) —
   every task belongs to exactly one user. Every query that touches
   tasks now filters by user_id, so one person can never see or modify
   another person's data. That check happening HERE, in the data layer,
   is deliberate — it means it's enforced no matter what calls into it.

Postgres syntax differences from SQLite you'll notice below:
  - SERIAL PRIMARY KEY instead of INTEGER PRIMARY KEY AUTOINCREMENT
  - %s placeholders instead of ?
  - RETURNING id lets us get a new row's id back from an INSERT directly,
    instead of SQLite's cursor.lastrowid
"""

import psycopg2
import psycopg2.extras
from datetime import date
from typing import List, Optional

from models import Task
from config import DATABASE_URL


def _connect():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db() -> None:
    """Create tables if they don't exist yet. Safe to call every startup."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_on TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    created_on TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS completions (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    completed_date TEXT NOT NULL
                )
            """)
        conn.commit()


# ---- Users ----

def create_user(username: str, password_hash: str) -> dict:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, created_on) "
                "VALUES (%s, %s, %s) RETURNING id",
                (username, password_hash, date.today().isoformat()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
    return get_user_by_username(username) or {"id": new_id, "username": username}


def get_user_by_username(username: str) -> Optional[dict]:
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, password_hash FROM users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


# ---- Tasks (all scoped to a user_id) ----

def _row_to_task(row, completion_dates) -> Task:
    task = Task(name=row[1], kind=row[2], id=row[0])
    task.created_on = date.fromisoformat(row[3])
    task.completed_dates = [date.fromisoformat(d) for d in completion_dates]
    return task


def get_all_tasks(user_id: int) -> List[Task]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, kind, created_on FROM tasks WHERE user_id = %s",
                (user_id,),
            )
            task_rows = cur.fetchall()
            tasks = []
            for row in task_rows:
                cur.execute(
                    "SELECT completed_date FROM completions WHERE task_id = %s",
                    (row[0],),
                )
                comp_rows = cur.fetchall()
                tasks.append(_row_to_task(row, [c[0] for c in comp_rows]))
            return tasks


def get_task(task_id: int, user_id: int) -> Optional[Task]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, kind, created_on FROM tasks WHERE id = %s AND user_id = %s",
                (task_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            cur.execute(
                "SELECT completed_date FROM completions WHERE task_id = %s", (task_id,)
            )
            comp_rows = cur.fetchall()
            return _row_to_task(row, [c[0] for c in comp_rows])


def insert_task(user_id: int, name: str, kind: str) -> Task:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (user_id, name, kind, created_on) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (user_id, name, kind, date.today().isoformat()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
    return get_task(new_id, user_id)


def add_completion(task_id: int, user_id: int, on: date = None) -> bool:
    """Returns False if the task doesn't exist OR doesn't belong to this user."""
    on = on or date.today()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM tasks WHERE id = %s AND user_id = %s", (task_id, user_id)
            )
            if not cur.fetchone():
                return False
            cur.execute(
                "SELECT id FROM completions WHERE task_id = %s AND completed_date = %s",
                (task_id, on.isoformat()),
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO completions (task_id, completed_date) VALUES (%s, %s)",
                    (task_id, on.isoformat()),
                )
        conn.commit()
    return True


def delete_task(task_id: int, user_id: int) -> bool:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, user_id)
            )
            deleted = cur.rowcount > 0
        conn.commit()
        return deleted
