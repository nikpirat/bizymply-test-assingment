from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from station_health.supplied import DATABASE_PATH


def connect(path: Path, *, check_same_thread: bool = True) -> sqlite3.Connection:
    connection = sqlite3.connect(path, check_same_thread=check_same_thread)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def database_path() -> Path:
    """Database location; overridable via ``STATION_HEALTH_DB``."""
    return Path(os.environ.get("STATION_HEALTH_DB", DATABASE_PATH))


def get_connection() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request, always closed.

    FastAPI may run a sync dependency and a sync endpoint on different
    threadpool threads, so the same-thread check is disabled. The connection
    is never shared between requests, so this is safe.
    """
    connection = connect(database_path(), check_same_thread=False)
    try:
        yield connection
    finally:
        connection.close()
