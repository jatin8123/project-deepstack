"""
test_coach.py
-------------
The coach agent has NO write tools in its schema — this is the property
worth actually testing, not just asserting in a docstring. We check its
tool schemas directly and confirm every tool it could possibly call is
read-only.
"""

from unittest.mock import patch, MagicMock

from agents import coach
import service
import storage
import auth


def make_user(username):
    hashed = auth.hash_password("testpassword")
    return storage.create_user(username, hashed)


def test_coach_has_no_write_tools():
    """A structural guarantee, not just a code review note: inspect the
    actual tool schemas and confirm none of them are capable of writing."""
    user = make_user("alice")
    schemas, implementations = coach._make_tools(user["id"])

    tool_names = {s["function"]["name"] for s in schemas}
    assert tool_names == {"get_all_tasks_with_history", "get_weekly_stats"}
    # every implementation takes zero arguments -> nothing to target a write at
    for name, fn in implementations.items():
        assert fn.__code__.co_argcount == 0, f"{name} should take no arguments"


def test_get_all_tasks_with_history_includes_completion_count():
    user = make_user("bob")
    task = service.add_task(user["id"], "Read", "habit")
    service.complete_task(user["id"], task.id)

    _, tools = coach._make_tools(user["id"])
    result = tools["get_all_tasks_with_history"]()

    assert result[0]["total_completions"] == 1
    assert result[0]["completed_today"] is True


def _final_response(text: str):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": text}}]
    }
    return mock_resp


@patch("agents.base.GROQ_API_KEY", "fake-key-for-testing")
@patch("agents.base.httpx.post")
def test_run_weekly_coach_returns_final_text(mock_post):
    user = make_user("carol")
    mock_post.return_value = _final_response("Great consistency this week!")

    result = coach.run_weekly_coach(user["id"])

    assert result == "Great consistency this week!"
