"""
agent.py
--------
Your first AGENT, genuinely different from ai.py's one-shot calls:

  - ai.py: YOU decide what data goes in the prompt, send ONE message,
    get ONE reply. You did all the "what does the model need to know"
    thinking yourself, upfront.

  - agent.py (this file): you hand the model a set of TOOLS — read-only
    functions it can call — and a goal. The model decides, on its own,
    which tools to call and in what order, reads the results, and keeps
    going until it has enough to answer. This is a reasoning LOOP, not
    a single call. That loop (call model -> maybe call a tool -> feed
    result back -> call model again -> ...) is what "agent" means here.

This agent is deliberately READ-ONLY. Every tool it can call only reads
data, scoped to one user via closures (see _make_tools below) — the
agent has no tool capable of writing anything, and literally no way to
see another user's data, since the functions it's given don't even
accept a user_id argument. A reasoning mistake can produce a bad
suggestion; it can't corrupt your data.

Architectural note: this file sits ABOVE service.py, calling INTO it —
the same relationship api.py has with service.py. That's deliberate:
service.py must never import agent.py (that would create a circular
import, and would also be backwards — your core business logic
shouldn't depend on any particular AI feature built on top of it).
"""

import json
from typing import List

import httpx

from config import GROQ_API_KEY
import service

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "qwen/qwen3.8-27b"
MAX_ITERATIONS = 5  # safety limit — never loop forever if something misbehaves


class AgentConfigError(RuntimeError):
    """Raised when agent features are used without an API key configured."""
    pass


def _make_tools(user_id: int):
    """
    Builds the tool SCHEMAS (what we tell the model exists) and their
    real IMPLEMENTATIONS (actual Python functions), both bound to one
    user_id via closures. This is what makes the scoping automatic and
    airtight: the agent can request "get_pending_tasks", but the
    function it actually triggers already has user_id baked in — there
    is no parameter the model could pass to see someone else's data.
    """
    def get_pending_tasks():
        tasks = service.get_all_tasks(user_id)
        pending = [t for t in tasks if not t.is_completed_today()]
        return [
            {
                "name": t.name,
                "kind": t.kind,
                "streak": t.current_streak(),
                "category": t.category,
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
                    "Get the user's tasks and habits not yet completed today, "
                    "each with its kind, current streak, and category."
                ),
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_weekly_stats",
                "description": "Get the user's weekly completion rate (percentage).",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ]

    implementations = {
        "get_pending_tasks": get_pending_tasks,
        "get_weekly_stats": get_weekly_stats,
    }

    return schemas, implementations


SYSTEM_PROMPT = (
    "You are a daily planning assistant. You have tools to look up the "
    "user's pending tasks/habits and their weekly stats. Use the tools "
    "to gather what you need, then propose a short, prioritized plan for "
    "today: which 2-4 items to focus on first and why (e.g. protecting a "
    "streak, a quick win, weekly balance). Be concise and practical. "
    "Once you've called the tools you need, give your final plan as "
    "plain text, no markdown, and stop calling tools."
)


def run_daily_planner(user_id: int) -> str:
    """
    Runs the agent loop for one user and returns its final plan as text.
    """
    if not GROQ_API_KEY:
        raise AgentConfigError(
            "GROQ_API_KEY is not set. Get a free key from console.groq.com "
            "and set it as an environment variable to use agent features."
        )

    tool_schemas, implementations = _make_tools(user_id)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "What should I focus on today?"},
    ]

    for _ in range(MAX_ITERATIONS):
        response = httpx.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 400,
                "messages": messages,
                "tools": tool_schemas,
            },
            timeout=30.0,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Groq API error {response.status_code}: {response.text}")

        data = response.json()
        message = data["choices"][0]["message"]
        messages.append(message)

        tool_calls = message.get("tool_calls")
        if not tool_calls:
            # The model made its decision and stopped requesting tools —
            # this is the final answer.
            return (message.get("content") or "").strip()

        # The model wants information. Run each requested tool LOCALLY
        # (never on Groq's side — tool calls are just requests; WE choose
        # to execute them) and feed the result back into the conversation.
        for call in tool_calls:
            fn_name = call["function"]["name"]
            fn = implementations.get(fn_name)
            result = fn() if fn else {"error": f"Unknown tool: {fn_name}"}
            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(result),
            })
        # Loop again: the model now sees the tool results and decides
        # whether it needs more information or is ready to answer.

    return "I wasn't able to finish planning in time — try again in a moment."
