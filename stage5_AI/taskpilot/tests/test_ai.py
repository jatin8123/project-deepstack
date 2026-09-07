"""
test_ai.py
----------
These tests mock httpx.post itself, rather than calling the real Groq
API — no real API key, network access, or cost needed to run these.
We're testing OUR code's behavior (prompt construction, response
parsing, fallback handling), not whether the model itself gives good
answers, which a unit test can't meaningfully assert anyway.
"""

from unittest.mock import patch, MagicMock

import ai


def _fake_response(text: str, status_code: int = 200):
    """Build a fake httpx.Response-like object shaped like Groq's real
    (OpenAI-compatible) chat completions response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"choices": [{"message": {"content": text}}]}
    mock_resp.text = text
    return mock_resp


@patch("ai.GROQ_API_KEY", "fake-key-for-testing")
@patch("ai.httpx.post")
def test_parse_natural_language_task_valid_json(mock_post):
    mock_post.return_value = _fake_response('{"name": "Meditate", "kind": "habit"}')
    result = ai.parse_natural_language_task("meditate every morning")
    assert result == {"name": "Meditate", "kind": "habit"}


@patch("ai.GROQ_API_KEY", "fake-key-for-testing")
@patch("ai.httpx.post")
def test_parse_natural_language_task_handles_markdown_fences(mock_post):
    """LLMs sometimes wrap JSON in ```json fences even when told not to."""
    mock_post.return_value = _fake_response('```json\n{"name": "Buy milk", "kind": "task"}\n```')
    result = ai.parse_natural_language_task("buy milk")
    assert result == {"name": "Buy milk", "kind": "task"}


@patch("ai.GROQ_API_KEY", "fake-key-for-testing")
@patch("ai.httpx.post")
def test_parse_natural_language_task_falls_back_on_garbage(mock_post):
    """If the model returns something unparseable, we fall back instead of crashing."""
    mock_post.return_value = _fake_response("sorry, I don't understand")
    result = ai.parse_natural_language_task("xyz nonsense")
    assert result == {"name": "Xyz nonsense", "kind": "task"}


@patch("ai.GROQ_API_KEY", "fake-key-for-testing")
@patch("ai.httpx.post")
def test_categorize_task_strips_whitespace(mock_post):
    mock_post.return_value = _fake_response("  Health  \n")
    result = ai.categorize_task("Morning run")
    assert result == "Health"


@patch("ai.GROQ_API_KEY", "fake-key-for-testing")
@patch("ai.httpx.post")
def test_weekly_summary_with_no_tasks_skips_api_call(mock_post):
    result = ai.weekly_summary([])
    assert "add a few" in result.lower()
    mock_post.assert_not_called()  # shouldn't even call the API for an empty list


def test_missing_api_key_raises_clear_error():
    """Without an API key, we should fail with a clear message, not a cryptic HTTP error."""
    with patch("ai.GROQ_API_KEY", ""):
        try:
            ai.parse_natural_language_task("test")
            assert False, "expected AIConfigError"
        except ai.AIConfigError as e:
            assert "GROQ_API_KEY" in str(e)


@patch("ai.GROQ_API_KEY", "fake-key-for-testing")
@patch("ai.httpx.post")
def test_api_error_surfaces_actual_message(mock_post):
    """A non-200 response should raise with Groq's real error text, not a bare code."""
    mock_post.return_value = _fake_response('{"error": "invalid model"}', status_code=400)
    try:
        ai.categorize_task("Something")
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "400" in str(e)
        assert "invalid model" in str(e)
