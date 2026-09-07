"""
api.py
------
This is Tier 1 (Presentation), rewritten as a web API instead of the
terminal menu in cli.py. Compare this file to cli.py: every route here
maps to a handler in cli.py, and both call the EXACT SAME service.py
functions the exact same way. service.py and storage.py did not change
one bit for this phase — proof the Phase 1-2 layering was worth it.

Run with:
    uvicorn api:app --reload
Then open:
    http://127.0.0.1:8000        -> the web UI
    http://127.0.0.1:8000/docs   -> FastAPI's auto-generated API explorer
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import service
import storage
from schemas import TaskCreate, TaskOut, StatsOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts (before 'yield') and once when
    it shuts down (after 'yield'). We only need the startup half —
    making sure the DB/tables exist before any request comes in."""
    storage.init_db()
    yield


app = FastAPI(title="TaskPilot API", lifespan=lifespan)
STATIC_DIR = Path(__file__).parent / "static"


def _to_out(task) -> TaskOut:
    """Translate an internal Task object into the API's public TaskOut shape."""
    return TaskOut(
        id=task.id,
        name=task.name,
        kind=task.kind,
        created_on=task.created_on.isoformat(),
        completed_today=task.is_completed_today(),
        streak=task.current_streak(),
    )


# ---- API routes (the actual "backend") ----

@app.get("/api/tasks", response_model=List[TaskOut])
def list_tasks():
    return [_to_out(t) for t in service.get_all_tasks()]


@app.post("/api/tasks", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate):
    task = service.add_task(payload.name, payload.kind)
    return _to_out(task)


@app.post("/api/tasks/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: int):
    task = service.complete_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _to_out(task)


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    if not service.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")


@app.get("/api/stats", response_model=StatsOut)
def stats():
    return StatsOut(weekly_completion_rate=service.weekly_completion_rate())


# ---- Serve the frontend (static HTML/CSS/JS) ----

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
