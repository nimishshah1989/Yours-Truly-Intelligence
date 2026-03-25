"""Backward-compat shim — canonical location is core/database.py."""
from core.database import *  # noqa: F401,F403
from core.database import (  # noqa: F401
    Base,
    SessionLocal,
    SessionReadOnly,
    engine,
    engine_readonly,
    get_db,
    get_readonly_db,
    init_db,
)
