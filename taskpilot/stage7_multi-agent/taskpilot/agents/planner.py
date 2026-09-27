"""
agents/planner.py
------------------
The daily planner agent from Phase 6, moved into the agents package
now that there's more than one agent. Its job is unchanged — only the
loop it runs on (agents.base.run_tool_loop) is now shared instead of
duplicated per-agent.

New in Phase 7: its get_pending_tasks tool now also returns priority
and nudge_time. If the scheduler or nudge agents have already run for
this user, the planner will simply see that data show up — it never
calls those agents directly, it just reads the same shared task table
they wrote to.
"""

import service
from agents.base import run_tool_loop, AgentConfigError  # re-exported for convenience

SYSTEM_PROMPT = (
    "You are a daily planning assistant. You have tools to look up the "
    "user's pending tasks/habits (including any priority order or "
    "suggested reminder times set by other planning agents, if present) "
    "and their weekly stats. Use the tools to gather what you need, then "
    "propose a short, prioritized plan for today: which 2-4 items to "
    "focus on first and why. Be concise and practical. Once you've "
    "called the tools you need, give your final plan as plain text, no "
    "markdown, and stop calling tools."
)


def _make_tools(user_id: int):
    def get_pending_tasks():
        tasks = service.get_all_tasks(user_id)
        pending = [t for t in tasks if not t.is_completed_today()]
        return [
            {
                "name": t.name,
                "kind": t.kind,
                "streak": t.current_streak(),
                "category": t.category,
                "priority": t.priority,
                "nudge_time": t.nudge_time,
            }
            for t in pending
        ]

    def get_weekly_stats():
        return {"weekly_completion_rate": service.weekly_completion_rate(user_id)}

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "get_pending_tasks",
                "description": (
                    "Get the user's pending tasks/habits, including any "
                    "priority or nudge time already set by other agents."
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
        "get_pending_tasks": get_pending_tasks,
        "get_weekly_stats": get_weekly_stats,
    }
    return schemas, implementations


def run_daily_planner(user_id: int) -> str:
    tool_schemas, implementations = _make_tools(user_id)
    return run_tool_loop(
        SYSTEM_PROMPT, "What should I focus on today?", tool_schemas, implementations
    )
