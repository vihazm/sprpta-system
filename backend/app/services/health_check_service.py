"""Health checks: about once a minute the backend times the web app, itself and the database.

Every reading is saved (health_checks), and a change of state is noted (health_events), so
the System health page can show uptime, response times and what happened. The loop starts
with the API (see main.py) and runs inside it, because there is no background worker.
If the database is down the readings cannot be saved, so they wait in memory and are saved
once it is back; that way the outage still shows up afterwards.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import HealthCheck, HealthEvent

log = logging.getLogger("sprpta.health")

INTERVAL_SECONDS = 60
KEEP_DAYS = 31
TIMEOUT_SECONDS = 5

SERVICE_NAMES = {"web": "Web app", "api": "API", "database": "Database"}
# A reading slower than this counts as "slow".
SLOW_MS = {"web": 1000, "api": 500, "database": 200}

STARTED_AT = datetime.now(UTC)  # when this copy of the API started


@dataclass(frozen=True)
class Reading:
    service: str
    status: str  # "ok", "slow" or "down"
    latency_ms: int | None
    detail: str | None = None
    taken_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def _answered(service: str, started: float) -> Reading:
    latency = round((time.perf_counter() - started) * 1000)
    if latency > SLOW_MS[service]:
        return Reading(service, "slow", latency, f"Answered in {latency} ms, the limit is {SLOW_MS[service]} ms")
    return Reading(service, "ok", latency)


def _down(service: str, detail: str) -> Reading:
    return Reading(service, "down", None, detail)


async def _timed_get(service: str, client: httpx.AsyncClient, url: str) -> Reading:
    started = time.perf_counter()
    try:
        response = await client.get(url)
    except httpx.TimeoutException:
        return _down(service, f"No answer within {TIMEOUT_SECONDS} seconds")
    except httpx.HTTPError:
        return _down(service, "Could not connect")
    if response.status_code >= 500:
        return _down(service, f"Replied with status {response.status_code}")
    return _answered(service, started)


async def check_web() -> Reading:
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        return await _timed_get("web", client, settings.web_url)


async def check_api(app: FastAPI) -> Reading:
    """Calls the API's own /health through its whole stack, without going over the network."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://api", timeout=TIMEOUT_SECONDS
    ) as client:
        return await _timed_get("api", client, "/health")


def _query_database() -> Reading:
    started = time.perf_counter()
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
    except Exception:
        return _down("database", "Could not connect")
    return _answered("database", started)


async def take_readings(app: FastAPI) -> list[Reading]:
    return list(
        await asyncio.gather(asyncio.to_thread(_query_database), check_api(app), check_web())
    )


def _note_database_start(db: Session) -> None:
    """Notes each start of the database server once, however often the API restarts."""
    started = db.scalar(text("select pg_postmaster_start_time()"))
    known = db.scalar(
        select(HealthEvent.id).where(
            HealthEvent.service == "database", HealthEvent.status == "started", HealthEvent.occurred_at == started
        )
    )
    if known is None:
        db.add(HealthEvent(service="database", status="started", occurred_at=started))


def save_readings(readings: list[Reading]) -> None:
    with SessionLocal() as db:
        for reading in readings:
            previous = db.scalar(
                select(HealthCheck.status)
                .where(HealthCheck.service == reading.service)
                .order_by(HealthCheck.id.desc())
                .limit(1)
            )
            db.add(
                HealthCheck(
                    service=reading.service,
                    status=reading.status,
                    latency_ms=reading.latency_ms,
                    checked_at=reading.taken_at,
                )
            )
            # A first reading that is fine is not news; any other change is.
            if previous != reading.status and (previous is not None or reading.status != "ok"):
                db.add(
                    HealthEvent(
                        service=reading.service,
                        status=reading.status,
                        detail=reading.detail,
                        occurred_at=reading.taken_at,
                    )
                )

        _note_database_start(db)
        cutoff = datetime.now(UTC) - timedelta(days=KEEP_DAYS)
        db.execute(delete(HealthCheck).where(HealthCheck.checked_at < cutoff))
        db.execute(delete(HealthEvent).where(HealthEvent.occurred_at < cutoff))
        db.commit()


async def run_checks(app: FastAPI) -> None:
    """One round of checks, saved straight away. Used by the "Run all checks now" button."""
    await asyncio.to_thread(save_readings, await take_readings(app))


def _note_api_start() -> None:
    with SessionLocal() as db:
        db.add(HealthEvent(service="api", status="started", occurred_at=STARTED_AT))
        db.commit()


async def health_check_loop(app: FastAPI) -> None:
    try:
        await asyncio.to_thread(_note_api_start)
    except Exception as error:
        log.warning("Could not note the API start: %s", error)

    unsaved: list[Reading] = []
    while True:
        unsaved += await take_readings(app)
        try:
            await asyncio.to_thread(save_readings, unsaved)
            unsaved.clear()
        except Exception as error:
            log.warning("Could not save %d health readings, will try again: %s", len(unsaved), error)
        await asyncio.sleep(INTERVAL_SECONDS)
