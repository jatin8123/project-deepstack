"""
api.py
------
Phase 4 update: added /api/register and /api/token for account creation
and login, and every task route now requires Depends(get_current_user) —
FastAPI runs that check before the route body executes, and injects
whichever user the token belongs to. Every service.* call below now
passes current_user["id"], so each user only ever sees their own tasks.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import service
import storage
import auth
from schemas import TaskCreate, TaskOut, StatsOut, UserCreate, UserOut, Token


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_db()
    yield


app = FastAPI(title="TaskPilot API", lifespan=lifespan)
STATIC_DIR = Path(__file__).parent / "static"


def _to_out(task) -> TaskOut:
    return TaskOut(
        id=task.id,
        name=task.name,
        kind=task.kind,
        created_on=task.created_on.isoformat(),
        completed_today=task.is_completed_today(),
        streak=task.current_streak(),
    )


# ---- Auth routes ----

@app.post("/api/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate):
    if storage.get_user_by_username(payload.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    hashed = auth.hash_password(payload.password)
    user = storage.create_user(payload.username, hashed)
    return UserOut(id=user["id"], username=user["username"])


@app.post("/api/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2PasswordRequestForm expects standard form fields 'username' and
    'password' (not JSON) — this is what makes it compatible with
    FastAPI's built-in /docs 'Authorize' button, and with standard OAuth2
    tooling generally.
    """
    user = auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth.create_access_token(user["username"])
    return Token(access_token=token)


# ---- Task routes (all require a valid token) ----

@app.get("/api/tasks", response_model=List[TaskOut])
def list_tasks(current_user: dict = Depends(auth.get_current_user)):
    return [_to_out(t) for t in service.get_all_tasks(current_user["id"])]


@app.post("/api/tasks", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, current_user: dict = Depends(auth.get_current_user)):
    task = service.add_task(current_user["id"], payload.name, payload.kind)
    return _to_out(task)


@app.post("/api/tasks/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: int, current_user: dict = Depends(auth.get_current_user)):
    task = service.complete_task(current_user["id"], task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _to_out(task)


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, current_user: dict = Depends(auth.get_current_user)):
    if not service.delete_task(current_user["id"], task_id):
        raise HTTPException(status_code=404, detail="Task not found")


@app.get("/api/stats", response_model=StatsOut)
def stats(current_user: dict = Depends(auth.get_current_user)):
    return StatsOut(weekly_completion_rate=service.weekly_completion_rate(current_user["id"]))


# ---- Serve the frontend ----

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
