from __future__ import annotations

import sqlite3
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from station_health import repository
from station_health.auth import OperatorId
from station_health.db import get_connection
from station_health.schemas import PeakWindowOut, StarvationOut
from station_health.starvation import evaluate_starvation

router = APIRouter(prefix="/stations", tags=["stations"])

Connection = Annotated[sqlite3.Connection, Depends(get_connection)]

STATION_NOT_FOUND = "Station not found"


@router.get(
    "/{station_id}/starvation",
    response_model=StarvationOut,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token"},
        status.HTTP_404_NOT_FOUND: {"description": STATION_NOT_FOUND},
    },
)
def get_station_starvation(
    station_id: int,
    day: Annotated[
        date, Query(alias="date", description="Day to evaluate, YYYY-MM-DD (UTC).")
    ],
    operator_id: OperatorId,
    connection: Connection,
) -> StarvationOut:
    """Did the station meet the operator's morning-peak starvation rule?"""
    # Same 404 for "does not exist" and "belongs to another operator", so
    # station ids cannot be enumerated across operators.
    if not repository.station_belongs_to_operator(connection, station_id, operator_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=STATION_NOT_FOUND)

    config = repository.get_peak_config(connection, operator_id)
    window = config.window_for(day)
    readings = repository.get_readings_near_window(connection, station_id, window)
    result = evaluate_starvation(readings, config, day)

    return StarvationOut(
        station_id=station_id,
        date=day,
        starved=result.starved,
        empty_readings=result.empty_readings,
        min_empty_readings=result.min_empty_readings,
        readings_in_window=result.readings_in_window,
        peak_window=PeakWindowOut(start=result.window.start, end=result.window.end),
    )
