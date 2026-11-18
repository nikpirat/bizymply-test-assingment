"""Pure domain logic for the morning-peak starvation rule.

Nothing in this module touches the database or HTTP, so the rule can be
unit-tested exhaustively and reused (e.g. by a batch report) unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time


@dataclass(frozen=True, slots=True)
class PeakConfig:
    """An operator's starvation settings."""

    peak_start: time
    peak_end: time
    min_empty_readings: int

    def __post_init__(self) -> None:
        if self.peak_start >= self.peak_end:
            # The README describes a *morning* peak; a window that wraps past
            # midnight is not supported and would silently count nothing.
            raise ValueError("peak_start must be earlier than peak_end")
        if self.min_empty_readings < 1:
            raise ValueError("min_empty_readings must be positive")

    def window_for(self, day: date) -> PeakWindow:
        return PeakWindow(
            start=datetime.combine(day, self.peak_start, tzinfo=UTC),
            end=datetime.combine(day, self.peak_end, tzinfo=UTC),
        )


@dataclass(frozen=True, slots=True)
class PeakWindow:
    """A half-open UTC interval: ``start <= t < end``."""

    start: datetime
    end: datetime

    def contains(self, moment: datetime) -> bool:
        return self.start <= moment < self.end


@dataclass(frozen=True, slots=True)
class Reading:
    recorded_at: datetime
    bikes_available: int
    docks_total: int

    @property
    def in_service(self) -> bool:
        # A station reporting zero docks cannot hold bikes at all; treat it as
        # offline/out of service rather than as a replenishment problem.
        return self.docks_total > 0

    @property
    def is_empty(self) -> bool:
        return self.in_service and self.bikes_available == 0


@dataclass(frozen=True, slots=True)
class StarvationResult:
    window: PeakWindow
    min_empty_readings: int
    readings_in_window: int
    empty_readings: int

    @property
    def starved(self) -> bool:
        return self.empty_readings >= self.min_empty_readings


def evaluate_starvation(
    readings: list[Reading],
    config: PeakConfig,
    day: date,
) -> StarvationResult:
    """Apply the starvation rule to a station's readings for ``day``.

    * Only readings inside the half-open peak window are considered.
    * Readings are counted per distinct timestamp, so a duplicated sample
      cannot inflate the count. A timestamp counts as empty if any reading
      at that instant reports an empty, in-service station.
    * Readings from stations with ``docks_total == 0`` are never empty.
    """
    window = config.window_for(day)

    empty_by_timestamp: dict[datetime, bool] = {}
    for reading in readings:
        if not window.contains(reading.recorded_at):
            continue
        key = reading.recorded_at
        empty_by_timestamp[key] = empty_by_timestamp.get(key, False) or reading.is_empty

    return StarvationResult(
        window=window,
        min_empty_readings=config.min_empty_readings,
        readings_in_window=len(empty_by_timestamp),
        empty_readings=sum(empty_by_timestamp.values()),
    )
