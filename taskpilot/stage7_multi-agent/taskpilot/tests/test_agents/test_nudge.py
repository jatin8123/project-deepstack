"""
test_nudge.py
--------------
Beyond the usual per-agent tests, test_nudge_sees_priority_set_by_scheduler
below is the one that actually proves the "communicate through the data
layer" architecture works: it runs the scheduler agent's tool directly,
then the nudge agent's tool, with NO connection between them except the
shared database — exactly like running them as two separate API calls
on two different days would behave.
"""

import json
from unittest.mock import patch, MagicMock

from agents import nudge, scheduler
import service
import storage
import auth


def make_user(username):
    hashed = auth.hash_password("testpassword")
    return storage.create_user(username, hashed)


def test_set_task_nudge_time_persists_to_real_db():
    user = make_user("alice")
    task = service.add_task(user["id"], "Take vitamins", "habit")

    _, tools = nudge._make_tools(user["id"])
    result = tools["set_task_nudge_time"](task_id=task.id, time="08:00")

    assert result["success"] is True
    reloaded = service.get_all_tasks(user["id"])[0]
    assert reloaded.nudge_time == "08:00"


def test_cannot_set_nudge_time_on_another_users_task():
    alice = make_user("alice")
    bob = make_user("bob")
    task = service.add_task(alice["id"], "Alice's task", "task")

    _, bob_tools = nudge._make_tools(bob["id"])
    result = bob_tools["set_task_nudge_time"](task_id=task.id, time="09:00")

    assert result["success"] is False


def test_nudge_sees_priority_set_by_scheduler_through_shared_data_only():
    """No direct call between scheduler and nudge here — scheduler writes
    via its own tool, nudge reads via its own, separate tool. If this
    passes, the two agents are genuinely only coupled through storage."""
    user = make_user("carol")
    task = service.add_task(user["id"], "Deep work block", "task")

    _, scheduler_tools = scheduler._make_tools(user["id"])
    scheduler_tools["set_task_priority"](task_id=task.id, priority=1)

    _, nudge_tools = nudge._make_tools(user["id"])
    pending = nudge_tools["get_pending_tasks"]()

    assert pending[0]["priority"] == 1


def _tool_call_response(tool_name: str, arguments: dict, call_id: str = "call_1"):
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
                    "function": {"name": tool_name, "arguments": json.dumps(arguments)},
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
def test_run_nudge_writes_time_via_full_loop(mock_post):
    user = make_user("dave")
    task = service.add_task(user["id"], "Evening walk", "habit")

    mock_post.side_effect = [
        _tool_call_response("get_pending_tasks", {}),
        _tool_call_response("set_task_nudge_time", {"task_id": task.id, "time": "18:00"}),
        _final_response("Suggested 18:00 for your evening walk."),
    ]

    result = nudge.run_nudge(user["id"])

    assert result == "Suggested 18:00 for your evening walk."
    reloaded = service.get_all_tasks(user["id"])[0]
    assert reloaded.nudge_time == "18:00"
