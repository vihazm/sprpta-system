from datetime import datetime, timedelta
from itertools import count

import pytest

from app.core.enums import ComplaintStatus, RejectionType, VehicleType
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.models import Area, Complaint, ComplaintCategory, ComplaintMedium, Severity, Vehicle
from tests.conftest import make_user, sign_in

URL = "/api/admin/statistics"
NUMBERS = count(1)


class Setup:
    """Two areas, the lists a routed case needs, and the administrator signed in."""


@pytest.fixture
def s(db, client, galle) -> Setup:
    s = Setup()
    s.galle = galle
    s.matara = Area(name="Matara")
    s.medium = ComplaintMedium(name="WhatsApp")
    s.category = ComplaintCategory(name="Reckless driving")
    s.critical = Severity(name="Critical", rank=1, forward_days=0, decide_days=1, close_days=3, rating_weight=8)
    s.low = Severity(name="Low", rank=4, forward_days=3, decide_days=14, close_days=30, rating_weight=1)
    db.add_all([s.matara, s.medium, s.category, s.critical, s.low])
    db.flush()
    s.bus = Vehicle(vehicle_number="NB-2345", vehicle_type=VehicleType.BUS, registered_area_id=galle.id)
    db.add(s.bus)
    s.l1 = make_user(db, "office@sprpta.test", UserRole.L1)
    s.officer = make_user(db, "gihan@sprpta.test", UserRole.L2, area_id=galle.id)
    make_user(db, "admin@sprpta.test", UserRole.ADMIN)
    sign_in(client, "admin@sprpta.test")
    return s


def complaint(db, s: Setup, *, days_ago: float = 1, severity=None, area=None, **changes) -> Complaint:
    """A forwarded case registered `days_ago` days ago, forwarded at once."""
    registered = datetime.now(LOCAL) - timedelta(days=days_ago)
    fields = dict(
        reference_number=f"SPRPTA-2026-{next(NUMBERS):06d}",
        status=ComplaintStatus.FORWARDED,
        entered_by_user_id=s.l1.id,
        medium_id=s.medium.id,
        complainant_name="Kamala Fernando",
        contact_phone="0771234567",
        subject="Reckless overtaking",
        category_id=s.category.id,
        severity_id=(severity or s.low).id,
        vehicle_id=s.bus.id,
        area_id=(area or s.galle).id,
        assigned_l2_user_id=s.officer.id,
        registered_at=registered,
        forwarded_at=registered,
    )
    c = Complaint(**{**fields, **changes})
    db.add(c)
    db.commit()
    return c


def test_only_the_admin_may_see_statistics(client, db, s):
    client.post("/api/auth/logout")
    assert client.get(URL).status_code == 401
    sign_in(client, "office@sprpta.test")
    assert client.get(URL).status_code == 403


def test_counts_cover_registered_complaints_only_and_hold_nothing_personal(client, db, s):
    complaint(db, s)
    complaint(db, s, area=s.matara, severity=s.critical)
    complaint(db, s, status=ComplaintStatus.REJECTED, rejection_type=RejectionType.SPAM, rejection_reason="Spam")
    db.add(Complaint(status=ComplaintStatus.DRAFT, entered_by_user_id=s.l1.id, complainant_name="Kamala Fernando"))
    db.commit()

    response = client.get(URL)
    stats = response.json()
    assert stats["total"] == 3
    by_status = {row["key"]: row["count"] for row in stats["by_status"]}
    assert by_status["forwarded"] == 2 and by_status["rejected"] == 1 and "draft" not in by_status
    assert stats["by_area"] == [{"key": "Galle", "count": 2}, {"key": "Matara", "count": 1}]
    assert [row["key"] for row in stats["by_severity"]] == ["Critical", "Low"]  # in order of severity
    assert stats["by_medium"] == [{"key": "WhatsApp", "count": 3}]
    assert [o["name"] for o in stats["options"]["areas"]] == ["Galle", "Matara"]
    # Masked for the administrator: no names, phone numbers or subjects anywhere in the answer.
    for personal in ("Kamala", "0771234567", "Reckless overtaking"):
        assert personal not in response.text


def test_filters_narrow_every_figure(client, db, s):
    complaint(db, s, days_ago=1)
    complaint(db, s, days_ago=40, area=s.matara)
    complaint(db, s, days_ago=40, severity=s.critical)

    today = datetime.now(LOCAL).date()
    assert client.get(URL, params={"area_id": s.matara.id}).json()["total"] == 1
    assert client.get(URL, params={"severity_id": s.critical.id}).json()["total"] == 1
    assert client.get(URL, params={"date_from": str(today - timedelta(days=7))}).json()["total"] == 1
    assert client.get(URL, params={"date_to": str(today - timedelta(days=7))}).json()["total"] == 2
    bad = client.get(URL, params={"date_from": str(today), "date_to": str(today - timedelta(days=1))})
    assert bad.status_code == 422


def test_time_targets_count_calendar_days_without_the_paused_time(client, db, s):
    registered = datetime.now(LOCAL) - timedelta(days=10)
    # Critical: forwarded the same day (on time, target 0), decided after 2 days (late, target 1).
    complaint(db, s, days_ago=10, severity=s.critical, decided_at=registered + timedelta(days=2), status=ComplaintStatus.UNDER_REVIEW)
    # Low: forwarded after 5 days, but 3 of them were spent Incomplete, so it is on time (target 3).
    complaint(db, s, days_ago=10, forwarded_at=registered + timedelta(days=5), paused_total=timedelta(days=3))

    rows = {row["severity"]: row for row in client.get(URL).json()["time_targets"]}
    critical, low, total = rows["Critical"], rows["Low"], rows["All severities"]
    assert critical["forward"] == {"target_days": 0, "finished": 1, "on_time": 1, "average_days": 0.0}
    assert critical["decide"] == {"target_days": 1, "finished": 1, "on_time": 0, "average_days": 2.0}
    assert critical["close"]["finished"] == 0 and critical["close"]["average_days"] is None
    assert low["forward"] == {"target_days": 3, "finished": 1, "on_time": 1, "average_days": 2.0}
    assert total["forward"] == {"target_days": None, "finished": 2, "on_time": 2, "average_days": 1.0}


def test_overdue_counts_follow_the_level_2_rule(client, db, s):
    complaint(db, s, days_ago=2, severity=s.critical)  # past decide-by (1 day)
    complaint(db, s, days_ago=5, severity=s.critical, decided_at=datetime.now(LOCAL), status=ComplaintStatus.AWAITING_IMPLEMENTATION)  # past close-by (3)
    complaint(db, s, days_ago=2)  # Low: within its targets

    assert client.get(URL).json()["overdue"] == {"total": 2, "awaiting_decision": 1, "awaiting_close": 1}
