from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from seed import build_database
from station_health.app import app
from station_health.db import connect, get_connection


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return build_database(tmp_path / "station_health.db")


@pytest.fixture
def client(database_path: Path) -> Iterator[TestClient]:
    """API client wired to a freshly seeded, per-test database."""

    def _override() -> Iterator:
        connection = connect(database_path, check_same_thread=False)
        try:
            yield connection
        finally:
            connection.close()

    app.dependency_overrides[get_connection] = _override
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()

