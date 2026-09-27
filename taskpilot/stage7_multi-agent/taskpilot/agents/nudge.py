"""
agents/nudge.py
-----------------
Decides a suggested reminder time per pending task/habit and writes it
back via set_task_nudge_time. Like the scheduler, this is a narrow
write-capable agent: it can only set a time string on the user's own
tasks.

This agent reads the SAME get_pending_tasks-style data the scheduler
uses, INCLUDING any priority the scheduler already set. This is the
"communicate through the data layer" pattern in action: run the
scheduler first and the nudge agent second, and the nudge agent's tool
results will already reflect the scheduler's decisions — with no
direct call between the two agents at all. Run them in the other
order, or run nudge alone, and priority will simply be absent (None);
nothing breaks either way.
"""

import service
from agents.base import run_tool_loop

SYSTEM_PROMPT = (
    "You are a reminder-timing assistant. You have a tool to see the "
    "user's pending tasks/habits (including priority order, if another "
    "agent has already set one) and a tool to set a suggested reminder "
    "time (24-hour HH:MM) on each. Habits with an active streak should "
    "get earlier, more protected times. If priorities are present, "
    "higher-priority items (lower priority number) should get earlier "
    "times too. Call get_pending_tasks, then set_task_nudge_time once "
    "per task. Finish with a short plain-text summary, no markdown."
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
                "priority": t.priority,  # may already be set by the scheduler agent
            }
            for t in pending
        ]

    def set_task_nudge_time(task_id: int, time: str):
        ok = service.set_task_nudge_time(user_id, task_id, time)
        return {"success": ok, "task_id": task_id, "nudge_time": time}

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "get_pending_tasks",
                "description": (
                    "Get the user's pending tasks/habits with id, kind, "
                    "streak, and priority (if already set)."
                ),
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "set_task_nudge_time",
                "description": "Set a suggested reminder time (24-hour HH:MM) on one task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer", "description": "The id of the task."},
                        "time": {
                            "type": "string",
                            "description": "Suggested time, 24-hour HH:MM, e.g. '07:30'.",
                        },
                    },
                    "required": ["task_id", "time"],
                },
            },
        },
    ]
    implementations = {
        "get_pending_tasks": get_pending_tasks,
        "set_task_nudge_time": set_task_nudge_time,
    }
    return schemas, implementations


def run_nudge(user_id: int) -> str:
    tool_schemas, implementations = _make_tools(user_id)
    return run_tool_loop(
        SYSTEM_PROMPT,
        "Suggest reminder times for my pending tasks.",
        tool_schemas,
        implementations,
    )
