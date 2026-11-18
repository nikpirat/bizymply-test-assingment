# Notes

## Endpoint

`GET /stations/{station_id}/starvation?date=YYYY-MM-DD` with `Authorization: Bearer <token>`

```json
{
  "station_id": 101,
  "date": "2026-09-15",
  "starved": true,
  "empty_readings": 3,
  "min_empty_readings": 3,
  "readings_in_window": 5,
  "peak_window": {"start": "2026-09-15T08:00:00Z", "end": "2026-09-15T10:00:00Z"}
}
```

Errors: `401` missing/unknown token · `404` station not found **or owned by another operator** (identical body) · `422` missing/invalid `date` or non-integer id.

## Assumptions that affect behaviour

- **`date` is a UTC calendar day**; the peak window is `[date + peak_start, date + peak_end)` in UTC.
- **Duplicate readings** (same station, same instant) count once. If duplicates disagree, the instant counts as empty if any of them is empty. Station 104 is therefore *not* starved (2 distinct empty readings, not 3).
- **`docks_total == 0` readings are never "empty"**: the station is treated as out of service, not as needing replenishment. Station 103 is therefore *not* starved. Such readings still count towards `readings_in_window`.
- **Empty readings need not be consecutive**: the rule counts them, it doesn't look for a run.
- **No data is not starvation**: a day with no readings returns `starved: false, readings_in_window: 0`, so clients can tell "healthy" from "unknown".
- **Peak windows don't cross midnight** (`peak_start < peak_end`); other configs are rejected as invalid.
- Naive timestamps (no offset) would be treated as UTC; non-UTC offsets are converted.
- An operator with no config row is a server-side data fault (500), not a client error.

## Incomplete / out of scope

- Tokens remain the static in-code mapping (no hashing, expiry or rotation).
- No range or bulk endpoint (e.g. "all starved stations this week").
- No logging/metrics beyond FastAPI defaults.

## Changes to the supplied setup

- None needed to the run commands. The DB path can optionally be overridden with `STATION_HEALTH_DB`.
- `db.connect()` gained an optional `check_same_thread` keyword (backwards compatible).
- `tests/conftest.py` gained a `client` fixture that points the app at a per-test seeded database.
- Developed on Python 3.14; FastAPI 0.115 emits an `asyncio.iscoroutinefunction` DeprecationWarning there (library-side, harmless).
