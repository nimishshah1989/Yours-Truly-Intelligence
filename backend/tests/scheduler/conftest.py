"""Conftest for scheduler tests — uses real RDS for integration tests."""

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
