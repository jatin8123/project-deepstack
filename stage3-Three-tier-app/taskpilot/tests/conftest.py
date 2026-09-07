"""
conftest.py
-----------
pytest automatically finds and loads this file. It's where shared test
setup lives — in our case, a "fixture" that gives EVERY test its own
brand-new, empty database, so tests never interfere with each other or
with your real taskpilot.db.

`autouse=True` means this runs automatically before every single test,
without each test needing to ask for it by name.
"""

import sys
from pathlib import Path

# Let tests import storage.py, service.py, models.py from the project root.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import storage


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """
    tmp_path: a pytest built-in — a unique temporary folder, auto-created
              and auto-cleaned-up for each test.
    monkeypatch: a pytest built-in for temporarily overriding a value
              (here, storage.DB_PATH) for the duration of one test only.
    """
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    storage.init_db()
    yield  # the test runs at this point
    # (no cleanup needed — tmp_path deletes itself automatically)
