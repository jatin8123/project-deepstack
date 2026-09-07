"""
ai.py
-----
This is the ONLY file in the app that knows an LLM exists. It talks to
Groq Cloud's API and returns ordinary Python data — strings, dicts.
Nothing about "AI" leaks into service.py, storage.py, or api.py; they
just call functions here and get back normal values.

Provider swap note: this file was originally written against Anthropic's
API. Switching to Groq only required editing THIS file — service.py,
api.py, and storage.py were untouched. That isolation is the entire
reason AI code lives in its own module: providers, models, and even
whole request formats can change underneath, and the rest of the app
never notices.

Groq's API is intentionally OpenAI-compatible, which is why this looks
a bit different from a raw Anthropic call:
  - the system prompt is a message in the `messages` list (role="system"),
    not a separate top-level `system` field
  - the reply comes back at choices[0].message.content, not content[0].text
"""

import json
from typing import List

import httpx

from config import GROQ_API_KEY

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "qwen/qwen3.8-27b"


class AIConfigError(RuntimeError):
    """Raised when AI features are used without an API key configured."""
    pass


def _call_llm(system_prompt: str, user_message: str, max_tokens: int = 300) -> str:
    """Low-level helper: sends one message to the LLM, returns the raw text reply."""
    if not GROQ_API_KEY:
        raise AIConfigError(
            "GROQ_API_KEY is not set. Get a free key from console.groq.com "
            "and set it as an environment variable to use AI features."
        )
    response = httpx.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        },
        timeout=30.0,
    )
    if response.status_code >= 400:
        # Surface Groq's actual error message instead of a bare status
        # code — this is what makes a future bug diagnosable in one look
        # instead of a guessing game.
        raise RuntimeError(f"Groq API error {response.status_code}: {response.text}")
    data = response.json()
    return data["choices"][0]["message"]["content"]


def parse_natural_language_task(text: str) -> dict:
    """
    Turn a free-text phrase like "meditate every morning" into structured
    data: {"name": "Meditate", "kind": "habit"}.
    """
    system = (
        "You convert a short user phrase describing a task or habit into "
        "structured JSON with exactly two keys: 'name' (a short, clean "
        "title, capitalized) and 'kind' (either 'task' for one-off items "
        "or 'habit' for recurring ones). Respond with ONLY the JSON "
        "object, no other text, no markdown fences."
    )
    raw = _call_llm(system, text, max_tokens=100)
    fallback = {"name": text.strip().capitalize(), "kind": "task"}
    return _safe_json(raw, fallback)


def categorize_task(name: str) -> str:
    """Suggest a single category label for a task/habit name."""
    system = (
        "Classify the following task or habit name into exactly ONE "
        "category from this list: Health, Work, Personal, Chores, "
        "Learning, Social, Finance, Other. Respond with ONLY the "
        "category word, nothing else."
    )
    raw = _call_llm(system, name, max_tokens=10)
    return raw.strip()


def weekly_summary(tasks: List) -> str:
    """
    Given a list of Task objects, produce a short natural-language
    summary of the week's patterns — a lightweight "AI coach" feature.
    """
    if not tasks:
        return "No tasks yet — add a few to start seeing weekly insights here."

    lines = [
        f"- {t.name} ({t.kind}): streak={t.current_streak()}, "
        f"done_today={t.is_completed_today()}, "
        f"total_completions_ever={len(t.completed_dates)}"
        for t in tasks
    ]
    data_block = "\n".join(lines)

    system = (
        "You are a supportive habit coach. Given a user's tasks/habits "
        "and their completion stats, write a brief (3-4 sentence), warm, "
        "encouraging weekly summary. Mention 1-2 specific wins and, if "
        "relevant, one gentle suggestion. Plain text only, no markdown."
    )
    return _call_llm(system, data_block, max_tokens=250)


def _safe_json(raw: str, fallback: dict) -> dict:
    """
    LLMs occasionally wrap JSON in markdown fences or add stray text
    even when told not to. This strips common wrapping and falls back
    to a safe default instead of crashing the app if parsing fails.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "name" in parsed and "kind" in parsed:
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return fallback
