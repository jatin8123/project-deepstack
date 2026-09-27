"""
agents/base.py
---------------
Shared machinery for every agent in this app: the actual reasoning loop
(call the model -> maybe run tools -> feed results back -> repeat) and
the safety iteration cutoff. Every agent (planner, coach, scheduler,
nudge) calls run_tool_loop() with its own system prompt and tool set —
none of them reimplement the loop itself.

This was extracted directly out of Phase 6's single agent.py once a
second agent needed the identical loop. Duplicating a loop like that
across two files is tolerable; across four, it stops being tolerable.
This is a normal, healthy refactor happening exactly when repetition
shows up for real — not an abstraction built in advance of need.
"""

import json
import httpx

from config import GROQ_API_KEY

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "qwen/qwen3.8-27b"
MAX_ITERATIONS = 5  # safety limit, shared by every agent


class AgentConfigError(RuntimeError):
    """Raised when an agent is used without an API key configured."""
    pass


def run_tool_loop(
    system_prompt: str,
    user_message: str,
    tool_schemas: list,
    implementations: dict,
    max_tokens: int = 400,
) -> str:
    """
    Runs the full agent loop and returns the model's final text answer.

    tool_schemas: the OpenAI/Groq-format tool definitions to send the model.
    implementations: {tool_name: python_function} — functions may take
    keyword arguments now (unlike Phase 6's argument-less tools), since
    write tools like set_task_priority need a task_id and a value.
    """
    if not GROQ_API_KEY:
        raise AgentConfigError(
            "GROQ_API_KEY is not set. Get a free key from console.groq.com "
            "and set it as an environment variable to use agent features."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
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
                "max_tokens": max_tokens,
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
            return (message.get("content") or "").strip()

        # A single message can request MULTIPLE tool calls at once (e.g.
        # the scheduler setting priority on several tasks in one go) —
        # we execute every one of them before looping back to the model.
        for call in tool_calls:
            fn_name = call["function"]["name"]
            fn = implementations.get(fn_name)
            if fn is None:
                result = {"error": f"Unknown tool: {fn_name}"}
            else:
                try:
                    args = json.loads(call["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = fn(**args)
            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(result),
            })

    return "I wasn't able to finish in time — try again in a moment."
