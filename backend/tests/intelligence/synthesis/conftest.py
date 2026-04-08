"""Conftest for synthesis tests — uses real RDS, not SQLite.

The parent conftest (tests/conftest.py) sets DATABASE_URL to sqlite:///:memory:.
We override that here so synthesis tests hit the real production database.
The .env file in backend/ has the real RDS connection string.
"""

import os
from pathlib import Path

# Load DATABASE_URL from .env BEFORE any core module import
env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()
