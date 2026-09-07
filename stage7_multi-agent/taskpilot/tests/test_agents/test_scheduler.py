"""
test_scheduler.py
------------------
The scheduler is the first WRITE-capable agent. The important thing to
prove here isn't just "it calls the API correctly" — it's that its
write tool genuinely can't touch another user's data, exactly like
every other write path in this app.
"""

import json
from unittest.mock import patch, MagicMock

from agents import scheduler
import service
import storage
import auth


def make_user(username):
    hashed = auth.hash_password("testpassword")
    return storage.create_user(username, hashed)


def test_set_task_priority_persists_to_real_db():
    user = make_user("alice")
    task = service.add_task(user["id"], "Important task", "task")

    _, tools = scheduler._make_tools(user["id"])
    result = tools["set_task_priority"](task_id=task.id, priority=1)

    assert result["success"] is True
    reloaded = service.get_all_tasks(user["id"])[0]
    assert reloaded.priority == 1


def test_cannot_set_priority_on_another_users_task():
    alice = make_user("alice")
    bob = make_user("bob")
    task = service.add_task(alice["id"], "Alice's task", "task")

    _, bob_tools = scheduler._make_tools(bob["id"])
    result = bob_tools["set_task_priority"](task_id=task.id, priority=1)

    assert result["success"] is False
    reloaded = service.get_all_tasks(alice["id"])[0]
    assert reloaded.priority is None


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
def test_run_scheduler_actually_writes_priority_via_full_loop(mock_post):
    """End-to-end through the real loop: model calls get_pending_tasks,
    then set_task_priority with a real argument, then finishes — and
    the priority should actually land in the database."""
    user = make_user("dave")
    task = service.add_task(user["id"], "Water plants", "task")

    mock_post.side_effect = [
        _tool_call_response("get_pending_tasks", {}),
        _tool_call_response("set_task_priority", {"task_id": task.id, "priority": 1}),
        _final_response("Set 'Water plants' as top priority."),
    ]

    result = scheduler.run_scheduler(user["id"])

    assert result == "Set 'Water plants' as top priority."
    reloaded = service.get_all_tasks(user["id"])[0]
    assert reloaded.priority == 1
