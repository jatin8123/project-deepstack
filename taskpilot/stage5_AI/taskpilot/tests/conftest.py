"""
conftest.py
-----------
Phase 4 update: instead of pointing at a temporary SQLite file, we now
point storage at a dedicated TEST Postgres database and wipe its tables
before every test. This keeps tests isolated from your real data,
exactly like Phase 2's fixture did, just adapted for a real DB server
instead of a throwaway file.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import storage
import config

TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/taskpilot_test"


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    monkeypatch.setattr(config, "DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setattr(storage, "DATABASE_URL", TEST_DATABASE_URL)
    storage.init_db()

    # Wipe all data before each test so tests never see each other's rows.
    with storage._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE users, tasks, completions RESTART IDENTITY CASCADE")
        conn.commit()

    yield
