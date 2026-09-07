"""
models.py
---------
This file defines *what a Task is* — its shape and its own small behaviors
(like calculating a streak). It knows nothing about files, databases, or
the menu the user sees. That separation is deliberate: in Phase 3, this
file barely changes even though storage and the UI get completely
replaced. This is the beginning of a "3-tier" mindset.

Phase 2 change: `id` is now Optional and defaults to None. In Phase 1 we
generated IDs ourselves with a counter. Now that a real database is doing
the storing, the DATABASE assigns IDs (via AUTOINCREMENT) the moment a
task is inserted — so a brand-new, not-yet-saved Task simply has no id yet.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional


@dataclass
class Task:
    """
    Represents a single task or habit.

    - kind="task"  -> a one-off to-do item (e.g. "Buy groceries")
    - kind="habit" -> a recurring item you complete repeatedly
                       (e.g. "Meditate", tracked with a streak)
    """
    name: str
    kind: str = "task"                     # "task" or "habit"
    id: Optional[int] = None               # assigned by the database on insert
    created_on: date = field(default_factory=date.today)
    completed_dates: List[date] = field(default_factory=list)

    def mark_complete(self, on: date = None):
        """Mark this task/habit complete for a given day (default: today)."""
        on = on or date.today()
        if on not in self.completed_dates:
            self.completed_dates.append(on)

    def is_completed_today(self) -> bool:
        return date.today() in self.completed_dates

    def current_streak(self) -> int:
        """
        Count consecutive days (ending today or yesterday) that this
        habit was completed. Only meaningful for kind="habit", but it
        won't error on a plain task — it'll just return 0 or 1.
        """
        if not self.completed_dates:
            return 0

        done = set(self.completed_dates)
        streak = 0
        cursor = date.today()

        # If today isn't done yet, the streak might still be "alive"
        # from yesterday — so start checking from yesterday in that case.
        if cursor not in done:
            cursor -= timedelta(days=1)

        while cursor in done:
            streak += 1
            cursor -= timedelta(days=1)

        return streak

    def to_dict(self) -> dict:
        """Convert this Task into plain data (for saving to JSON)."""
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "created_on": self.created_on.isoformat(),
            "completed_dates": [d.isoformat() for d in self.completed_dates],
        }

    @staticmethod
    def from_dict(data: dict) -> "Task":
        """Rebuild a Task object from plain data (loaded from JSON)."""
        task = Task(
            name=data["name"],
            kind=data.get("kind", "task"),
            id=data["id"],
        )
        task.created_on = date.fromisoformat(data["created_on"])
        task.completed_dates = [date.fromisoformat(d) for d in data["completed_dates"]]
        return task
