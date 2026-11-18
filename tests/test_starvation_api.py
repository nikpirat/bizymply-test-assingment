"""End-to-end tests for GET /stations/{id}/starvation against seeded data."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

METRO = {"Authorization": "Bearer metro-token"}
HARBOUR = {"Authorization": "Bearer harbour-token"}
PEAK_DAY = "2026-09-15"


def url(station_id: int | str) -> str:
    return f"/stations/{station_id}/starvation"


@pytest.mark.parametrize(
    ("headers", "station_id", "starved", "empty_readings", "readings_in_window"),
    [
        # Boundary readings at 07:45 and 10:00 and the 09-14 reading excluded.
        pytest.param(METRO, 101, True, 3, 5, id="101-boundaries"),
        pytest.param(METRO, 102, False, 2, 4, id="102-below-threshold"),
        # docks_total == 0: out of service, not starved.
        pytest.param(METRO, 103, False, 0, 3, id="103-zero-docks"),
        # Duplicate 08:00 row must not push 2 empty readings to 3.
        pytest.param(METRO, 104, False, 2, 3, id="104-duplicate-reading"),
        # Harbour: 07:30-09:30 window, threshold 2; 07:30 start inclusive.
        pytest.param(HARBOUR, 201, True, 2, 3, id="201-other-operator-config"),
        pytest.param(HARBOUR, 202, False, 1, 2, id="202-below-threshold"),
    ],
)
def test_seeded_stations(
    client: TestClient,
    headers: dict[str, str],
    station_id: int,
    starved: bool,
    empty_readings: int,
    readings_in_window: int,
) -> None:
    response = client.get(url(station_id), params={"date": PEAK_DAY}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["station_id"] == station_id
    assert body["date"] == PEAK_DAY
    assert body["starved"] is starved
    assert body["empty_readings"] == empty_readings
    assert body["readings_in_window"] == readings_in_window


def test_response_shape(client: TestClient) -> None:
    response = client.get(url(101), params={"date": PEAK_DAY}, headers=METRO)

    assert response.json() == {
        "station_id": 101,
        "date": PEAK_DAY,
        "starved": True,
        "empty_readings": 3,
        "min_empty_readings": 3,
        "readings_in_window": 5,
        "peak_window": {
            "start": "2026-09-15T08:00:00Z",
            "end": "2026-09-15T10:00:00Z",
        },
    }


def test_uses_the_authenticated_operators_window(client: TestClient) -> None:
    body = client.get(url(201), params={"date": PEAK_DAY}, headers=HARBOUR).json()

    assert body["min_empty_readings"] == 2
    assert body["peak_window"] == {
        "start": "2026-09-15T07:30:00Z",
        "end": "2026-09-15T09:30:00Z",
    }


def test_date_without_readings_reports_no_data(client: TestClient) -> None:
    response = client.get(url(101), params={"date": "2026-01-01"}, headers=METRO)

    assert response.status_code == 200
    body = response.json()
    assert (body["starved"], body["empty_readings"], body["readings_in_window"]) == (
        False,
        0,
        0,
    )


def test_previous_day_is_evaluated_independently(client: TestClient) -> None:
    body = client.get(url(101), params={"date": "2026-09-14"}, headers=METRO).json()

    assert (body["empty_readings"], body["starved"]) == (1, False)


# --- Tenant isolation ---------------------------------------------------------


@pytest.mark.parametrize(
    ("headers", "foreign_station"),
    [(METRO, 201), (METRO, 202), (HARBOUR, 101), (HARBOUR, 104)],
)
def test_other_operators_station_is_indistinguishable_from_missing(
    client: TestClient, headers: dict[str, str], foreign_station: int
) -> None:
    foreign = client.get(url(foreign_station), params={"date": PEAK_DAY}, headers=headers)
    missing = client.get(url(999_999), params={"date": PEAK_DAY}, headers=headers)

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


# --- Authentication -----------------------------------------------------------


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="missing"),
        pytest.param({"Authorization": "Bearer nope"}, id="unknown-token"),
        pytest.param({"Authorization": "metro-token"}, id="no-scheme"),
        pytest.param({"Authorization": "Basic metro-token"}, id="wrong-scheme"),
    ],
)
def test_rejects_unauthenticated_requests(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.get(url(101), params={"date": PEAK_DAY}, headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_auth_is_checked_before_station_existence(client: TestClient) -> None:
    # An anonymous caller must not learn anything about station ids either.
    response = client.get(url(999_999), params={"date": PEAK_DAY})

    assert response.status_code == 401


# --- Input validation ---------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({}, id="missing-date"),
        pytest.param({"date": "15-09-2026"}, id="wrong-format"),
        pytest.param({"date": "2026-02-30"}, id="impossible-date"),
    ],
)
def test_rejects_invalid_date(client: TestClient, params: dict[str, str]) -> None:
    response = client.get(url(101), params=params, headers=METRO)

    assert response.status_code == 422


def test_rejects_non_integer_station_id(client: TestClient) -> None:
    response = client.get(url("abc"), params={"date": PEAK_DAY}, headers=METRO)

    assert response.status_code == 422


# --- Storage robustness -------------------------------------------------------


def test_timestamps_with_z_suffix_are_handled(
    client: TestClient, database_path: Path
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            "INSERT INTO dock_readings (station_id, recorded_at, bikes_available,"
            " docks_total) VALUES (?, ?, ?, ?)",
            [
                (202, "2026-09-16T07:30:00Z", 0, 8),
                (202, "2026-09-16T09:29:59.500Z", 0, 8),
                (202, "2026-09-16T09:30:00Z", 0, 8),
            ],
        )

    body = client.get(url(202), params={"date": "2026-09-16"}, headers=HARBOUR).json()

    assert (body["empty_readings"], body["starved"]) == (2, True)
