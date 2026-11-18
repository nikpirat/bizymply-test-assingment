"""Data access for stations, operator configuration and readings.

Every station lookup is scoped by operator in SQL, so a station owned by a
different operator is indistinguishable from one that does not exist.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, time, timedelta

from station_health.starvation import PeakConfig, PeakWindow, Reading


class ConfigurationMissingError(RuntimeError):
    """An operator has no starvation configuration (a data/setup fault)."""


def station_belongs_to_operator(
    connection: sqlite3.Connection, station_id: int, operator_id: int
) -> bool:
    row = connection.execute(
        "SELECT 1 FROM stations WHERE id = ? AND operator_id = ?",
        (station_id, operator_id),
    ).fetchone()
    return row is not None


def get_peak_config(connection: sqlite3.Connection, operator_id: int) -> PeakConfig:
    row = connection.execute(
        """
        SELECT peak_start, peak_end, min_empty_readings
        FROM operator_configs
        WHERE operator_id = ?
        """,
        (operator_id,),
    ).fetchone()
    if row is None:
        raise ConfigurationMissingError(f"operator {operator_id} has no config")
    return PeakConfig(
        peak_start=time.fromisoformat(row["peak_start"]),
        peak_end=time.fromisoformat(row["peak_end"]),
        min_empty_readings=row["min_empty_readings"],
    )


def get_readings_near_window(
    connection: sqlite3.Connection, station_id: int, window: PeakWindow
) -> list[Reading]:
    """Return readings that *may* fall inside ``window``.

    The SQL filter is deliberately coarse (whole days either side, compared
    as text) so it can use ``idx_readings_station_time`` while staying
    correct regardless of how timestamps are serialised (``Z`` vs
    ``+00:00``, fractional seconds). Exact half-open filtering happens on
    parsed, timezone-aware datetimes in the domain layer.
    """
    lower = (window.start - timedelta(days=1)).date().isoformat()
    upper = (window.end + timedelta(days=2)).date().isoformat()
    rows = connection.execute(
        """
        SELECT recorded_at, bikes_available, docks_total
        FROM dock_readings
        WHERE station_id = ? AND recorded_at >= ? AND recorded_at < ?
        """,
        (station_id, lower, upper),
    ).fetchall()
    return [
        Reading(
            recorded_at=_parse_utc(row["recorded_at"]),
            bikes_available=row["bikes_available"],
            docks_total=row["docks_total"],
        )
        for row in rows
    ]


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        # The supplied contract says timestamps are UTC; treat naive ones so.
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
