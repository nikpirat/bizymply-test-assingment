from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class PeakWindowOut(BaseModel):
    start: datetime = Field(description="Inclusive start of the peak window (UTC).")
    end: datetime = Field(description="Exclusive end of the peak window (UTC).")


class StarvationOut(BaseModel):
    station_id: int
    date: date
    starved: bool = Field(description="True if empty_readings >= min_empty_readings.")
    empty_readings: int = Field(
        description="Distinct timestamps in the window where an in-service "
        "station had zero bikes available."
    )
    min_empty_readings: int = Field(description="The operator's configured threshold.")
    readings_in_window: int = Field(
        description="Distinct reading timestamps in the window; 0 means no data."
    )
    peak_window: PeakWindowOut
