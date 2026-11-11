import asyncio
import time
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.roles import UserRole
from app.main import app
from app.models import HealthCheck, HealthEvent, UsageLog
from app.services import health_check_service
from app.services.health_check_service import Reading, save_readings
from tests.conftest import make_user, sign_in

URL = "/api/admin/system-health"


def signed_in_admin(db, client) -> None:
    make_user(db, "admin@sprpta.test", UserRole.ADMIN, full_name="Sarah Admin")
    sign_in(client, "admin@sprpta.test")


def reading(service: str, status: str, latency: int | None, minutes_ago: float = 0, detail=None) -> Reading:
    return Reading(service, status, latency, detail, datetime.now(UTC) - timedelta(minutes=minutes_ago))


def statuses(body: dict) -> dict[str, str]:
    return {s["key"]: s["status"] for s in body["services"]}


# ---------------------------------------------------------------- access


def test_only_the_admin_may_open_system_health(client, db):
    assert client.get(URL).status_code == 401
    make_user(db, "office@sprpta.test", UserRole.L1)
    sign_in(client, "office@sprpta.test")
    assert client.get(URL).status_code == 403
    assert client.post(f"{URL}/checks").status_code == 403


# ---------------------------------------------------------------- reading


def test_before_any_reading_everything_is_unknown_but_the_database_answers(client, db):
    signed_in_admin(db, client)

    body = client.get(URL).json()
    assert statuses(body) == {"web": "unknown", "api": "unknown", "database": "unknown"}
    assert body["series"] == {"web": [], "api": [], "database": []}
    assert body["uptime"]["percent"] is None
    assert body["uptime"]["days"] == ["unknown"] * 30
    assert body["events"] == []
    assert body["checked_at"] is None
    assert body["database"]["connections"] >= 1
    assert body["database"]["max_connections"] > 0
    assert body["database"]["size_bytes"] > 0


def test_the_newest_reading_of_each_service_is_shown(client, db):
    signed_in_admin(db, client)
    save_readings(
        [
            reading("api", "ok", 100, minutes_ago=2),
            reading("api", "slow", 700, minutes_ago=1),
            reading("web", "ok", 40),
            reading("database", "down", None),
        ]
    )

    services = {s["key"]: s for s in client.get(URL).json()["services"]}
    assert (services["api"]["status"], services["api"]["latency_ms"]) == ("slow", 700)
    assert (services["web"]["status"], services["web"]["latency_ms"]) == ("ok", 40)
    assert (services["database"]["status"], services["database"]["latency_ms"]) == ("down", None)


def test_old_readings_are_not_shown_as_current(client, db):
    signed_in_admin(db, client)
    save_readings([reading("api", "ok", 100, minutes_ago=10)])
    assert statuses(client.get(URL).json())["api"] == "unknown"


def test_response_times_are_averaged_in_15_minute_steps(client, db):
    signed_in_admin(db, client)
    now = datetime.now(UTC)
    first = now.replace(minute=0, second=10, microsecond=0) - timedelta(hours=2)
    db.add_all(
        [
            HealthCheck(service="api", status="ok", latency_ms=100, checked_at=first),
            HealthCheck(service="api", status="ok", latency_ms=200, checked_at=first + timedelta(minutes=1)),
            HealthCheck(service="api", status="ok", latency_ms=50, checked_at=first + timedelta(minutes=20)),
            HealthCheck(service="api", status="down", latency_ms=None, checked_at=first + timedelta(minutes=40)),
            HealthCheck(service="api", status="ok", latency_ms=999, checked_at=now - timedelta(hours=30)),  # too old
        ]
    )
    db.commit()

    assert client.get(URL).json()["series"]["api"] == [150, 50]  # a failed reading has no time to average


# ---------------------------------------------------------------- uptime and events


def test_uptime_counts_readings_and_marks_the_days_with_an_outage(client, db):
    signed_in_admin(db, client)
    now = datetime.now(UTC)
    db.add_all(
        [HealthCheck(service="api", status="ok", latency_ms=90, checked_at=now - timedelta(minutes=m)) for m in range(3, 9)]
        + [HealthCheck(service="api", status="down", latency_ms=None, checked_at=now - timedelta(days=2))]
        + [HealthCheck(service="api", status="ok", latency_ms=90, checked_at=now - timedelta(days=2, minutes=5))]
    )
    db.commit()

    uptime = client.get(URL).json()["uptime"]
    assert uptime["percent"] == 87.5  # 7 of 8 readings were not "down"
    assert uptime["days"][-1] == "up"
    assert uptime["days"][-3] == "down"
    assert uptime["days"][-2] == "unknown"
    assert uptime["tracking_since"] is not None


def test_a_change_of_state_is_noted_once_and_the_last_outage_is_timed(client, db):
    signed_in_admin(db, client)
    save_readings([reading("database", "ok", 5, minutes_ago=30)])  # a healthy first reading is not news
    save_readings([reading("database", "ok", 5, minutes_ago=29)])
    assert db.query(HealthEvent).filter_by(service="database").filter(HealthEvent.status != "started").count() == 0

    save_readings([reading("database", "down", None, minutes_ago=20, detail="Could not connect")])
    save_readings([reading("database", "down", None, minutes_ago=19)])  # still down: no second event
    save_readings([reading("database", "ok", 6, minutes_ago=6)])

    body = client.get(URL).json()
    titles = [e["title"] for e in body["events"]]
    assert titles[:2] == ["Database is back to normal", "Database stopped responding"]
    assert body["events"][1]["tone"] == "crit" and body["events"][1]["detail"] == "Could not connect"
    outage = body["uptime"]["last_outage"]
    assert (outage["service_name"], outage["minutes"], outage["reason"]) == ("Database", 14, "Could not connect")


def test_an_outage_that_has_not_ended_has_no_end_time(client, db):
    signed_in_admin(db, client)
    save_readings([reading("web", "down", None, detail="Could not connect")])
    assert client.get(URL).json()["uptime"]["last_outage"]["minutes"] is None


def test_each_start_of_the_database_is_noted_only_once(db):
    save_readings([reading("database", "ok", 5)])
    save_readings([reading("database", "ok", 5)])
    assert db.query(HealthEvent).filter_by(service="database", status="started").count() == 1


def test_failed_sign_ins_and_locked_accounts_appear_as_events(client, db):
    signed_in_admin(db, client)
    make_user(db, "locked@sprpta.test", UserRole.L1, locked_until=datetime.now(UTC) + timedelta(minutes=10))
    assert client.get(URL).json()["events"][0]["title"] == "1 account is locked"

    db.add_all([UsageLog(event_type="login_failed") for _ in range(5)])
    db.commit()
    titles = [e["title"] for e in client.get(URL).json()["events"]]
    assert "5 failed sign-ins in the last hour" in titles and "1 account is locked" in titles


def test_old_readings_are_removed(db):
    old = datetime.now(UTC) - timedelta(days=40)
    db.add_all([HealthCheck(service="api", status="ok", latency_ms=1, checked_at=old), HealthEvent(service="api", status="slow", occurred_at=old)])
    db.commit()

    save_readings([reading("api", "ok", 100)])
    assert db.query(HealthCheck).filter(HealthCheck.checked_at < old + timedelta(days=1)).count() == 0
    assert db.query(HealthEvent).filter(HealthEvent.occurred_at < old + timedelta(days=1)).count() == 0


# ---------------------------------------------------------------- the checks themselves


def test_the_database_and_the_api_check_themselves(db):
    readings = {r.service: r for r in asyncio.run(health_check_service.take_readings(app))}
    assert readings["database"].status in ("ok", "slow") and readings["database"].latency_ms is not None
    assert readings["api"].status in ("ok", "slow") and readings["api"].latency_ms is not None


def test_an_unreachable_web_app_is_down(monkeypatch):
    monkeypatch.setattr(settings, "web_url", "http://127.0.0.1:9")
    web = asyncio.run(health_check_service.check_web())
    assert (web.status, web.latency_ms, web.detail) == ("down", None, "Could not connect")


def test_a_slow_answer_is_marked_slow():
    slow = health_check_service._answered("api", time.perf_counter() - 1)
    assert slow.status == "slow" and slow.latency_ms >= 1000
    assert health_check_service._answered("api", time.perf_counter()).status == "ok"


def test_running_the_checks_now_saves_fresh_readings(client, db, monkeypatch):
    monkeypatch.setattr(settings, "web_url", "http://127.0.0.1:9")
    signed_in_admin(db, client)

    response = client.post(f"{URL}/checks")
    assert response.status_code == 200
    body = response.json()
    assert statuses(body)["web"] == "down"
    assert statuses(body)["api"] in ("ok", "slow") and statuses(body)["database"] in ("ok", "slow")
    assert body["checked_at"] is not None


def test_the_dashboard_shows_the_same_services_and_response_times(client, db):
    signed_in_admin(db, client)
    save_readings([reading("api", "ok", 120), reading("web", "ok", 40), reading("database", "ok", 5)])

    body = client.get("/api/admin/dashboard").json()
    assert [(s["key"], s["status"]) for s in body["services"]] == [("web", "ok"), ("api", "ok"), ("database", "ok")]
    assert body["api_response_ms"] == [120]


def test_readings_wait_in_memory_while_the_database_cannot_save_them(db, monkeypatch):
    saves = []
    real_save = health_check_service.save_readings

    def flaky_save(readings):
        saves.append(len(readings))
        if len(saves) == 1:
            raise RuntimeError("the database is down")
        real_save(readings)

    monkeypatch.setattr(health_check_service, "save_readings", flaky_save)
    monkeypatch.setattr(health_check_service, "INTERVAL_SECONDS", 0.05)

    async def run_for_a_moment():
        task = asyncio.create_task(health_check_service.health_check_loop(app))
        await asyncio.sleep(1.5)
        task.cancel()

    asyncio.run(run_for_a_moment())
    assert saves[:2] == [3, 6]  # the first round was kept and saved together with the second
    assert db.query(HealthCheck).count() >= 6
