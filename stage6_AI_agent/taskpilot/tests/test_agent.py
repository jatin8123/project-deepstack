"""
test_agent.py
-------------
Two different kinds of tests here, testing two different things:

1. test_make_tools_* — uses the REAL database (via conftest.py's temp_db
   fixture), no mocking at all. This proves the tool-scoping mechanism
   itself is correct: a tool built for user A genuinely cannot see user
   B's data, because the closure never received user B's id in the
   first place.

2. test_run_daily_planner_* — mocks httpx.post to simulate a multi-turn
   conversation with the model (tool call -> tool result -> final
   answer), without needing a real API key or network access. This
   tests the LOOP logic: does it call tools, feed results back, and
   stop correctly.
"""

from unittest.mock import patch, MagicMock

import agent
import service


def make_user(username):
    import storage
    import auth
    hashed = auth.hash_password("testpassword")
    return storage.create_user(username, hashed)


# ---- Tool scoping (real DB, no mocking) ----

def test_tools_only_see_their_own_users_tasks():
    alice = make_user("alice")
    bob = make_user("bob")
    service.add_task(alice["id"], "Alice's pending task", "task")
    service.add_task(bob["id"], "Bob's pending task", "task")

    alice_schemas, alice_tools = agent._make_tools(alice["id"])
    result = alice_tools["get_pending_tasks"]()

    names = [t["name"] for t in result]
    assert "Alice's pending task" in names
    assert "Bob's pending task" not in names


def test_get_pending_tasks_excludes_completed_today():
    user = make_user("carol")
    incomplete = service.add_task(user["id"], "Not done yet", "task")
    done = service.add_task(user["id"], "Already done", "task")
    service.complete_task(user["id"], done.id)

    _, tools = agent._make_tools(user["id"])
    result = tools["get_pending_tasks"]()

    names = [t["name"] for t in result]
    assert "Not done yet" in names
    assert "Already done" not in names


def test_get_weekly_stats_returns_real_rate():
    user = make_user("dave")
    task = service.add_task(user["id"], "Stretch", "habit")
    service.complete_task(user["id"], task.id)

    _, tools = agent._make_tools(user["id"])
    result = tools["get_weekly_stats"]()

    assert "weekly_completion_rate" in result
    assert result["weekly_completion_rate"] > 0


# ---- Agent loop (mocked httpx.post) ----

def _tool_call_response(tool_name: str, call_id: str = "call_1"):
    """A model response that requests one tool call."""
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
    """A model response with no tool calls — the final answer."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": text}}]
    }
    return mock_resp


@patch("agent.GROQ_API_KEY", "fake-key-for-testing")
@patch("agent.httpx.post")
def test_agent_calls_tool_then_returns_final_plan(mock_post):
    user = make_user("erin")
    service.add_task(user["id"], "Morning run", "habit")

    # First call: model asks for pending tasks.
    # Second call: model has enough info, gives a final answer.
    mock_post.side_effect = [
        _tool_call_response("get_pending_tasks"),
        _final_response("Focus on your morning run to protect the streak."),
    ]

    plan = agent.run_daily_planner(user["id"])

    assert plan == "Focus on your morning run to protect the streak."
    assert mock_post.call_count == 2

    # Confirm the tool RESULT actually made it back into the conversation
    # sent on the second call — i.e. the loop really fed data back in,
    # not just called the API twice independently.
    second_call_messages = mock_post.call_args_list[1].kwargs["json"]["messages"]
    tool_result_messages = [m for m in second_call_messages if m.get("role") == "tool"]
    assert len(tool_result_messages) == 1
    assert "Morning run" in tool_result_messages[0]["content"]


@patch("agent.GROQ_API_KEY", "fake-key-for-testing")
@patch("agent.httpx.post")
def test_agent_stops_after_max_iterations(mock_post):
    """If the model never stops requesting tools, the loop must not run forever."""
    user = make_user("frank")
    mock_post.side_effect = [
        _tool_call_response("get_pending_tasks") for _ in range(agent.MAX_ITERATIONS)
    ]

    plan = agent.run_daily_planner(user["id"])

    assert "wasn't able to finish" in plan.lower()
    assert mock_post.call_count == agent.MAX_ITERATIONS


def test_missing_api_key_raises_clear_error():
    with patch("agent.GROQ_API_KEY", ""):
        user = make_user("grace")
        try:
            agent.run_daily_planner(user["id"])
            assert False, "expected AgentConfigError"
        except agent.AgentConfigError as e:
            assert "GROQ_API_KEY" in str(e)
