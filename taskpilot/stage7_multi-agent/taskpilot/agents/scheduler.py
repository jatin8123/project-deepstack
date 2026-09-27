"""
agents/scheduler.py
--------------------
The first WRITE-capable agent in this app. Unlike the planner and
coach (read-only, suggestions only), the scheduler can call
set_task_priority to actually persist a priority order onto tasks.

Worth noticing exactly how narrow the blast radius still is: the one
write tool this agent has can only set a priority NUMBER on a task
that already belongs to this user — service.set_task_priority enforces
that ownership check, same as every other write in this app. This
agent cannot create, delete, rename, or complete anything. A bad
decision here produces a bad ORDERING, never data loss or a
cross-user leak.

Communication with other agents happens THROUGH THE DATABASE, not
directly: this agent writes priority values here; the planner and
nudge agents read them back later, whenever they next run, via their
own get_pending_tasks tool. No agent ever calls another agent.
"""

import service
from agents.base import run_tool_loop

SYSTEM_PROMPT = (
    "You are a scheduling assistant. You have a tool to see the user's "
    "pending tasks/habits, and a tool to set a priority number on each "
    "(1 = do first). Call get_pending_tasks, decide a sensible priority "
    "order — consider habit streaks worth protecting, and a mix of "
    "quick wins vs important items — then call set_task_priority once "
    "per task to record that order. When done, give a short plain-text "
    "summary of the order you set, no markdown."
)


def _make_tools(user_id: int):
    def get_pending_tasks():
        tasks = service.get_all_tasks(user_id)
        pending = [t for t in tasks if not t.is_completed_today()]
        return [
            {
                "id": t.id,
                "name": t.name,
                "kind": t.kind,
                "streak": t.current_streak(),
                "category": t.category,
            }
            for t in pending
        ]

    def set_task_priority(task_id: int, priority: int):
        ok = service.set_task_priority(user_id, task_id, priority)
        return {"success": ok, "task_id": task_id, "priority": priority}

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "get_pending_tasks",
                "description": (
                    "Get the user's pending tasks/habits with id, kind, "
                    "streak, and category."
                ),
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "set_task_priority",
                "description": "Set a priority number (1 = highest, do first) on one task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "The id of the task to prioritize.",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority rank, 1 = do first.",
                        },
                    },
                    "required": ["task_id", "priority"],
                },
            },
        },
    ]
    implementations = {
        "get_pending_tasks": get_pending_tasks,
        "set_task_priority": set_task_priority,
    }
    return schemas, implementations


def run_scheduler(user_id: int) -> str:
    tool_schemas, implementations = _make_tools(user_id)
    return run_tool_loop(
        SYSTEM_PROMPT,
        "Please prioritize my pending tasks for today.",
        tool_schemas,
        implementations,
    )
