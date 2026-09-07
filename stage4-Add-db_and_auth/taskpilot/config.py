"""
config.py
---------
Centralizes settings that change between environments (your laptop vs.
a real server) instead of hardcoding them. Reading these from
environment variables — rather than writing them directly in code — is
standard practice: it means the same code can run against different
databases or with different secrets without being edited, just by
setting different environment variables wherever it runs.

For local development, if these env vars aren't set, we fall back to
sensible local defaults so you don't have to configure anything extra
just to run this on your laptop.
"""

import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/taskpilot",
)

# In real deployments this MUST be a long random secret, kept out of
# source control (e.g. injected as an env var by your hosting platform).
# The fallback here is only acceptable for local learning/dev.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
