"""
main.py
-------
The single entry point for running the app. Setup work — like making
sure the database and its tables exist — belongs here, not inside
cli.py, which should stay focused purely on the user-facing menu.

This separation matters more once Phase 3 adds a web entry point too:
both entry points can call storage.init_db() and then hand off to
their own presentation layer, without duplicating startup logic.
"""

import storage
from cli import run

if __name__ == "__main__":
    storage.init_db()
    run()
