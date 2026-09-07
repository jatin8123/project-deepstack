"""
test_planner.py
----------------
Same two kinds of tests as Phase 6's original agent tests:
1. Real-DB tests proving tool scoping is airtight (no mocking).
2. Mocked-httpx tests proving the tool-calling LOOP logic is correct.

Only the import paths changed (agents.planner, agents.base) now that
this agent lives in the agents/ package instead of a single agent.py.
"""

from unittest.mock import patch, MagicMock

from agents import planner
import service
import storage
import auth


def make_user(username):
    hashed = auth.hash_password("testpassword")
    return storage.create_user(username, hashed)


# ---- Tool scoping (real DB, no mocking) ----

def test_tools_only_see_their_own_users_tasks():
    alice = make_user("alice")
    bob = make_user("bob")
    service.add_task(alice["id"], "Alice's pending task", "task")
    service.add_task(bob["id"], "Bob's pending task", "task")

    _, alice_tools = planner._make_tools(alice["id"])
    result = alice_tools["get_pending_tasks"]()

    names = [t["name"] for t in result]
    assert "Alice's pending task" in names
    assert "Bob's pending task" not in names


def test_get_pending_tasks_excludes_completed_today():
    user = make_user("carol")
    service.add_task(user["id"], "Not done yet", "task")
    done = service.add_task(user["id"], "Already done", "task")
    service.complete_task(user["id"], done.id)

    _, tools = planner._make_tools(user["id"])
    result = tools["get_pending_tasks"]()

    names = [t["name"] for t in result]
    assert "Not done yet" in names
    assert "Already done" not in names


def test_get_pending_tasks_reflects_priority_set_by_scheduler():
    """The planner should see priority values even though it never
    calls the scheduler — it just reads the same shared task table."""
    user = make_user("dave")
    task = service.add_task(user["id"], "Important thing", "task")
    service.set_task_priority(user["id"], task.id, 1)

    _, tools = planner._make_tools(user["id"])
    result = tools["get_pending_tasks"]()

    assert result[0]["priority"] == 1


# ---- Agent loop (mocked httpx.post) ----

def _tool_call_response(tool_name: str, call_id: str = "call_1"):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": call_id,
                    "type": "function",
                    "function": {"name": tool_name, "arguments": "{}"},
                }],
            }
        }]
    }
    return mock_resp


def _final_response(text: str):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": text}}]
    }
    return mock_resp


@patch("agents.base.GROQ_API_KEY", "fake-key-for-testing")
@patch("agents.base.httpx.post")
def test_planner_calls_tool_then_returns_final_plan(mock_post):
    user = make_user("erin")
    service.add_task(user["id"], "Morning run", "habit")

    mock_post.side_effect = [
        _tool_call_response("get_pending_tasks"),
        _final_response("Focus on your morning run to protect the streak."),
    ]

    plan = planner.run_daily_planner(user["id"])

    assert plan == "Focus on your morning run to protect the streak."
    assert mock_post.call_count == 2


@patch("agents.base.GROQ_API_KEY", "")
def test_missing_api_key_raises_clear_error():
    user = make_user("grace")
    try:
        planner.run_daily_planner(user["id"])
        assert False, "expected AgentConfigError"
    except Exception as e:
        assert "GROQ_API_KEY" in str(e)
