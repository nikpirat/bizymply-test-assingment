"""Unit tests for the pure starvation rule (no DB, no HTTP)."""
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta, timezone

import pytest

from station_health.starvation import PeakConfig, Reading, evaluate_starvation

DAY = date(2026, 9, 15)
CONFIG = PeakConfig(peak_start=time(8, 0), peak_end=time(10, 0), min_empty_readings=2)


def at(hh: int, mm: int, day: date = DAY) -> datetime:
    return datetime(day.year, day.month, day.day, hh, mm, tzinfo=UTC)


def empty(moment: datetime, docks: int = 10) -> Reading:
    return Reading(recorded_at=moment, bikes_available=0, docks_total=docks)


def stocked(moment: datetime) -> Reading:
    return Reading(recorded_at=moment, bikes_available=5, docks_total=10)


def test_window_start_is_inclusive() -> None:
    result = evaluate_starvation([empty(at(8, 0))], CONFIG, DAY)
    assert result.empty_readings == 1


def test_window_end_is_exclusive() -> None:
    result = evaluate_starvation([empty(at(10, 0))], CONFIG, DAY)
    assert result.empty_readings == 0
    assert result.readings_in_window == 0


def test_last_instant_before_end_is_included() -> None:
    moment = at(10, 0) - timedelta(microseconds=1)
    assert evaluate_starvation([empty(moment)], CONFIG, DAY).empty_readings == 1


def test_readings_before_window_and_on_other_days_are_ignored() -> None:
    readings = [
        empty(at(7, 59)),
        empty(at(8, 15, date(2026, 9, 14))),
        empty(at(8, 15, date(2026, 9, 16))),
    ]
    assert evaluate_starvation(readings, CONFIG, DAY).empty_readings == 0


def test_threshold_is_at_least_not_strictly_greater() -> None:
    exactly = evaluate_starvation([empty(at(8, 0)), empty(at(8, 15))], CONFIG, DAY)
    below = evaluate_starvation([empty(at(8, 0)), stocked(at(8, 15))], CONFIG, DAY)
    assert exactly.starved is True
    assert below.starved is False


def test_empty_readings_need_not_be_consecutive() -> None:
    readings = [empty(at(8, 0)), stocked(at(8, 15)), empty(at(8, 30))]
    assert evaluate_starvation(readings, CONFIG, DAY).starved is True


def test_duplicate_timestamps_count_once() -> None:
    readings = [empty(at(8, 0)), empty(at(8, 0)), stocked(at(8, 15))]
    result = evaluate_starvation(readings, CONFIG, DAY)
    assert result.empty_readings == 1
    assert result.readings_in_window == 2
    assert result.starved is False


def test_conflicting_duplicates_count_as_empty_once() -> None:
    readings = [stocked(at(8, 0)), empty(at(8, 0))]
    assert evaluate_starvation(readings, CONFIG, DAY).empty_readings == 1


def test_same_instant_in_different_offsets_is_a_duplicate() -> None:
    plus_one = timezone(timedelta(hours=1))
    readings = [empty(at(8, 0)), empty(datetime(2026, 9, 15, 9, 0, tzinfo=plus_one))]
    assert evaluate_starvation(readings, CONFIG, DAY).empty_readings == 1


def test_zero_dock_station_is_not_counted_as_empty() -> None:
    readings = [empty(at(8, 0), docks=0), empty(at(8, 15), docks=0)]
    result = evaluate_starvation(readings, CONFIG, DAY)
    assert result.empty_readings == 0
    assert result.readings_in_window == 2
    assert result.starved is False


def test_no_readings_is_not_starved_and_reports_no_data() -> None:
    result = evaluate_starvation([], CONFIG, DAY)
    assert (result.starved, result.empty_readings, result.readings_in_window) == (
        False,
        0,
        0,
    )


def test_window_is_reported_in_utc() -> None:
    window = evaluate_starvation([], CONFIG, DAY).window
    assert (window.start, window.end) == (at(8, 0), at(10, 0))


@pytest.mark.parametrize(
    ("start", "end", "minimum"),
    [(time(10, 0), time(8, 0), 1), (time(8, 0), time(8, 0), 1), (time(8, 0), time(9, 0), 0)],
)
def test_invalid_config_is_rejected(start: time, end: time, minimum: int) -> None:
    with pytest.raises(ValueError):
        PeakConfig(peak_start=start, peak_end=end, min_empty_readings=minimum)
