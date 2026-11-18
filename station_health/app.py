from __future__ import annotations

from fastapi import FastAPI

from station_health.routes import router


app = FastAPI(title="Station Health")
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
