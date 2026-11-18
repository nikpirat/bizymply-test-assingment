# Take-home: Station Health Service

Thanks for making time for this exercise. It is a small, self-contained service created for the interview; Bizimply will not use your solution in production.

## The problem

A bike-share company manages stations across a city. Each station contains **docks**: individual spaces where bicycles are parked and locked. During the morning commute, some stations repeatedly have no bikes available, leaving riders unable to start a journey.

The company's operations team wants to review past station availability so it can decide where to investigate or adjust bike replenishment.

The service is shared by multiple bike-share companies. Each company is an **operator** and manages its own set of stations. An authenticated operations team may access all stations belonging to its operator, but no stations belonging to another operator.

## Your task

Build an API endpoint that lets an authenticated operator check whether one of its stations met the **starvation rule** on a selected date.

Each operator has:

- a morning peak window in UTC;
- a minimum number of empty readings.

A station qualifies as starved when it has at least the configured minimum number of readings with `bikes_available == 0` during its peak window on the requested date. The peak window includes its start time and excludes its end time.

The result must state whether the station qualified as starved and include the empty-reading count supporting that result.

Operators must not be able to access another operator's stations or discover whether those stations exist.

Choose the endpoint route, response structure, and internal organisation you consider appropriate. Add tests that give confidence in the behaviour.

## What is supplied

The project includes:

- a minimal runnable FastAPI application;
- a SQLite connection helper;
- a token-to-operator mapping;
- `seed.py`, which creates a SQLite database containing synthetic operators, configurations, stations, and historical readings;
- a working pytest setup with basic scaffold tests.

Each historical reading records:

- `station_id`;
- `recorded_at`, an ISO 8601 UTC timestamp;
- `bikes_available`;
- `docks_total`, the station's total number of bicycle parking spaces at that time.

Readings are normally recorded every 15 minutes.

Inspect the supplied schema and data as you would when joining an existing service. Where behaviour is unspecified, make a reasonable assumption and continue.

## Time and tools

Spend no more than **three hours**, including setup and testing. Stop when you reach the limit and submit what you have. An incomplete submission is acceptable; briefly identify what remains unfinished.

Use the tools you would normally use at work, including AI coding assistants. You are responsible for the solution you submit and should be prepared to explain and modify it during the debrief.

If the supplied setup prevents you from getting started, contact us so we can resolve it and adjust the time allowance.

## Setup

Python 3.12 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed.py
pytest
uvicorn station_health.app:app --reload
```

The supplied test suite should report eight passing tests before you begin. The health endpoint is available at `GET /health`.

Do not modify the synthetic seed data merely to make your implementation pass.

## Notes

Include a short `NOTES.md` containing:

- assumptions that materially affect the service's behaviour;
- incomplete functionality;
- any changes needed to the supplied setup or run commands.

Short bullets are enough. Design history, AI transcripts, and a lengthy report are not required.

## Submitting

Send a ZIP file or a link to a private repository containing your implementation, tests, and `NOTES.md`.

Exclude `.venv/`, cache directories, and the generated `station_health.db` file.

The submission will form the basis of a 60-minute interview. We will walk through your solution, discuss a small requirement change, and ask you to implement that change using the tools you normally use.
