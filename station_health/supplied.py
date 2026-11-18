from __future__ import annotations

from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parent.parent / "station_health.db"

TOKENS: dict[str, int] = {
    "metro-token": 1,
    "harbour-token": 2,
}
