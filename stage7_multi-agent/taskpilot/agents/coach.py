"""
agents/coach.py
----------------
Read-only agent, same safety principle as Phase 6: it reviews the
user's tasks/habits and completion history and suggests habit tweaks
in plain language. It has NO write tools in its schema at all — that's
a stronger guarantee than "we just choose not to call the write
functions." There is no write capability for this agent to misuse,
even in principle.
"""

import service
from agents.base import run_tool_loop

SYSTEM_PROMPT = (
    "You are a supportive habit coach reviewing a user's week. You have "
    "tools to see all their tasks/habits (with streaks, categories, and "
    "completion history) and their weekly completion rate. Identify 1-2 "
    "things going well and one gentle, specific suggestion for "
    "improvement (e.g. a neglected category, a habit at risk of "
    "breaking its streak). Keep it brief (3-4 sentences), warm, plain "
    "text, no markdown. You cannot change anything — you can only "
    "observe and suggest."
)


def _make_tools(user_id: int):
    def get_all_tasks_with_history():
        tasks = service.get_all_tasks(user_id)
        return [
            {
                "name": t.name,
                "kind": t.kind,
                "category": t.category,
                "streak": t.current_streak(),
                "completed_today": t.is_completed_today(),
                "total_completions": len(t.completed_dates),
            }
            for t in tasks
        ]

    def get_weekly_stats():
        return {"weekly_completion_rate": service.weekly_completion_rate(user_id)}

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "get_all_tasks_with_history",
                "description": (
                    "Get all the user's tasks/habits with streak, "
                    "category, and completion history."
                ),
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_weekly_stats",
                "description": "Get the user's weekly completion rate.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ]
    implementations = {
        "get_all_tasks_with_history": get_all_tasks_with_history,
        "get_weekly_stats": get_weekly_stats,
    }
    return schemas, implementations


def run_weekly_coach(user_id: int) -> str:
    tool_schemas, implementations = _make_tools(user_id)
    return run_tool_loop(
        SYSTEM_PROMPT,
        "How did my week go, and what should I adjust?",
        tool_schemas,
        implementations,
    )
