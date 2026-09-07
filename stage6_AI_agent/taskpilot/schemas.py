"""
schemas.py
----------
Pydantic models define the API's public "contract" — exactly what shape
of JSON comes in and goes out over HTTP. This is intentionally separate
from models.py's Task class: Task is your internal domain object (used
everywhere inside the app), while these are the external wire format.

Why bother with two classes that look similar? Because they serve
different masters. Task can change freely to suit internal logic
(e.g. add an internal-only field) without breaking every client that
calls your API — and vice versa, you can reshape the API response
without touching how Task works internally. This separation is standard
practice in real backend services.
"""

from pydantic import BaseModel


class TaskCreate(BaseModel):
    """What the client sends us when creating a task."""
    name: str
    kind: str = "task"


class TaskOut(BaseModel):
    """What we send back to the client — a flattened, JSON-friendly view of a Task."""
    id: int
    name: str
    kind: str
    created_on: str
    completed_today: bool
    streak: int
    category: str | None = None


class TaskSuggestion(BaseModel):
    """Phase 5: AI's structured guess at a task from free text."""
    name: str
    kind: str


class TextInput(BaseModel):
    text: str


class SummaryOut(BaseModel):
    summary: str


class PlanOut(BaseModel):
    """Phase 6: the agent's daily plan output."""
    plan: str


class StatsOut(BaseModel):
    weekly_completion_rate: float


class UserCreate(BaseModel):
    """What a client sends to register a new account."""
    username: str
    password: str


class UserOut(BaseModel):
    """What we send back about a user — notably, never the password or its hash."""
    id: int
    username: str


class Token(BaseModel):
    """What we send back after a successful login."""
    access_token: str
    token_type: str = "bearer"
