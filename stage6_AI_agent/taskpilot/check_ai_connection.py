"""
check_ai_connection.py
-----------------------
A standalone diagnostic script — NOT part of the app itself. Run this
directly to test whether your GROQ_API_KEY and network can reach Groq
at all, completely independent of FastAPI, service.py, the browser, or
anything else in TaskPilot.

If this script works but the app's "Suggest" button doesn't, the
problem is somewhere in the app's wiring (stale --reload, wrong file
saved, wrong venv, etc.) — not your key or connectivity.

If this script ALSO fails, the error message below will tell you
exactly why: bad key, bad model name, rate limit, or a network issue.

Run it with:
    python3 check_ai_connection.py
"""

import os
import sys

import httpx

API_KEY = os.environ.get("GROQ_API_KEY", "")
API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "qwen/qwen3.8-27b"


def main():
    print("=== TaskPilot AI connectivity check (Groq) ===\n")

    if not API_KEY:
        print("FAIL: GROQ_API_KEY is not set in this terminal session.")
        print("Fix: export GROQ_API_KEY='gsk_...' and re-run this script")
        print("     (in the SAME terminal you're about to run this in).")
        sys.exit(1)

    masked = API_KEY[:8] + "..." + API_KEY[-4:] if len(API_KEY) > 12 else "(too short?)"
    print(f"Found GROQ_API_KEY: {masked}")
    print(f"Using model: {MODEL}")
    print("Sending a minimal test request to Groq...\n")

    try:
        response = httpx.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 20,
                "messages": [
                    {"role": "user", "content": "Say 'connection ok' and nothing else."}
                ],
            },
            timeout=30.0,
        )
    except httpx.ConnectError as e:
        print(f"FAIL: could not connect to Groq's servers at all.")
        print(f"Details: {e}")
        print("This usually means a network/firewall/proxy issue, not your key.")
        sys.exit(1)
    except httpx.TimeoutException:
        print("FAIL: request timed out after 30 seconds.")
        print("This usually means a slow/blocked network connection.")
        sys.exit(1)

    print(f"HTTP status code: {response.status_code}\n")

    if response.status_code == 200:
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        print(f"SUCCESS. Model replied: {text!r}")
        print("\nYour API key, network, and model name are all working correctly.")
        print("If the app's Suggest button still fails, the problem is in the")
        print("app's own code/config, not your Groq connection.")
    elif response.status_code == 401:
        print("FAIL: 401 Unauthorized — your API key is invalid or revoked.")
        print(f"Raw response: {response.text}")
        print("Fix: generate a fresh key at console.groq.com and re-export it.")
    elif response.status_code == 400:
        print("FAIL: 400 Bad Request — often an invalid/decommissioned model name.")
        print(f"Raw response: {response.text}")
        print("Fix: check current model IDs at console.groq.com/docs/models")
    elif response.status_code == 429:
        print("FAIL: 429 — rate limited, or you've hit a free-tier usage limit.")
        print(f"Raw response: {response.text}")
    else:
        print(f"FAIL: unexpected status {response.status_code}")
        print(f"Raw response: {response.text}")


if __name__ == "__main__":
    main()
