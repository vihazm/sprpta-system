"""DEVELOPMENT ONLY: synthetic daily bus operation history (1 Jan 2026 to 15 Nov 2026) and sample complaints.

    python -m app.scripts.seed_dev_history                      show what would be created (changes nothing)
    python -m app.scripts.seed_dev_history --confirm            create it
    python -m app.scripts.seed_dev_history --remove --confirm   delete what this script created

Everything is fictional and labelled as synthetic test data:
  - Fictional buses numbered "SP SY-####" with permits "SYN-P-####", owned by "Synthetic Owner NN".
  - Every other bus in the database (for example the client's imported buses) gets test trips too, on the routes
    of its own area, with a synthetic driver and conductor. Real people are never put on a test trip.
  - People named "Synthetic Driver 07" and so on, with team_label "SYNTHETIC-TEST-DATA".
  - Every trip's remarks say "Synthetic test data"; complaints whose subject starts "[SYNTHETIC]" and whose
    client_request_id starts "syn-hist-".
It is deterministic (a fixed random seed) and repeatable: a second run finds what exists and adds nothing. It writes no
audit_log rows and changes no existing record. It needs the demo areas and accounts from `app.scripts.seed`.
It refuses to run unless APP_ENV=development and the database is on this computer.

What it creates: published daily trips with verified duty for most of the year, a few approved and pending ones in
the last week (so My Daily Bus Records and the Admin steps have something to show), and complaints against drivers,
conductors, owners, services and others, each linked to a trip so Quick Entry auto-fill and the dashboard can be tried.
"""

import argparse
import random
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from urllib.parse import urlparse

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import ComplaintStatus, DutyRecordStatus, PersonType, PlaceKind, VehicleType
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.db.session import SessionLocal
from app.models import (
    Area,
    Complaint,
    ComplaintCategory,
    ComplaintDutySnapshot,
    ComplaintMedium,
    ComplaintTargetType,
    DailyTrip,
    Permit,
    Person,
    RouteStand,
    Severity,
    TripDuty,
    User,
    Vehicle,
)
from app.scripts.seed_dev_complaints import check_environment

START, END = date(2026, 1, 1), date(2026, 11, 15)
LABEL = "SYNTHETIC-TEST-DATA"
PREFIX = "syn-hist-"
AREA_NAMES = ["Galle", "Matara", "Hambantota"]
BUSES_PER_AREA = 8
MARKER = "Synthetic test data"
PLATE = "SP SY-"  # the fictional buses
IMPORTED_SAMPLE_DAYS = 20  # earlier days on which every other bus also has trips
DRIVERS, CONDUCTORS = 18, 18
COMPLAINTS = 120
RECENT = END - timedelta(days=6)  # from here on, some records are still pending or only approved

ROUTES = [  # (area, route name, origin, destination)
    ("Galle", "[SYNTHETIC] Galle - Matara (route 2)", "Galle", "Matara"),
    ("Galle", "[SYNTHETIC] Galle - Elpitiya (route 24)", "Galle", "Elpitiya"),
    ("Galle", "[SYNTHETIC] Galle - Hikkaduwa (route 11)", "Galle", "Hikkaduwa"),
    ("Matara", "[SYNTHETIC] Matara - Akuressa (route 5)", "Matara", "Akuressa"),
    ("Matara", "[SYNTHETIC] Matara - Weligama (route 6)", "Matara", "Weligama"),
    ("Matara", "[SYNTHETIC] Matara - Deniyaya (route 9)", "Matara", "Deniyaya"),
    ("Hambantota", "[SYNTHETIC] Hambantota - Tangalle (route 31)", "Hambantota", "Tangalle"),
    ("Hambantota", "[SYNTHETIC] Hambantota - Tissa (route 33)", "Hambantota", "Tissamaharama"),
]
TRIP_TIMES = [(time(6, 30), time(9, 0)), (time(14, 15), time(16, 45))]
SUBJECTS = ["Overcharging on the fare", "Rude behaviour", "Bus left the stand early", "Reckless driving",
            "No ticket issued", "Bus not in a safe condition", "Skipped a stop", "Overcrowding"]


@dataclass
class TripPlan:
    day: date
    bus: int  # index into the bus list
    slot: int  # 0 or 1
    status: str  # published | approved | draft


def _people_names() -> list[tuple[str, PersonType]]:
    out = [(f"Synthetic Driver {i:02d}", PersonType.DRIVER) for i in range(1, DRIVERS + 1)]
    out += [(f"Synthetic Conductor {i:02d}", PersonType.CONDUCTOR) for i in range(1, CONDUCTORS + 1)]
    out += [(f"Synthetic Owner {i:02d}", PersonType.OWNER) for i in range(1, 13)]
    return out


def _buses() -> list[tuple[str, str, int]]:
    """(vehicle number, area, owner number): the same list on every run."""
    return [(f"{PLATE}{n:04d}", AREA_NAMES[(n - 1) // BUSES_PER_AREA], (n - 1) % 12 + 1)
            for n in range(1, BUSES_PER_AREA * len(AREA_NAMES) + 1)]


def plan_trips() -> list[TripPlan]:
    rng = random.Random(20260115)
    plan = []
    for offset in range((END - START).days + 1):
        day = START + timedelta(days=offset)
        for bus in range(len(_buses())):
            if rng.random() < 0.12:  # the bus did not run
                continue
            for slot in (0, 1):
                if slot == 1 and rng.random() < 0.35:
                    continue
                status = "published"
                if day >= RECENT:
                    status = rng.choice(["published", "published", "approved", "draft", "draft"])
                plan.append(TripPlan(day, bus, slot, status))
    return plan


def plan_complaints(trips: list[TripPlan]) -> list[tuple[int, TripPlan, str, str]]:
    """(number, trip, target, status), drawn from published trips only."""
    rng = random.Random(7)
    published = [t for t in trips if t.status == "published"]
    targets = ["driver", "conductor", "owner", "bus_service", "other"]
    statuses = ["forwarded"] * 6 + ["incomplete"] * 2 + ["draft"] * 2
    return [(n, rng.choice(published), targets[n % 5], rng.choice(statuses)) for n in range(1, COMPLAINTS + 1)]


def _ends(name: str) -> tuple[str, str]:
    """Origin and destination from a route name such as '24/1 Avithtawa - Elpitiya' or 'Galle - Matara (route 2)'."""
    clean = re.sub(r"\s*\(.*?\)\s*$", "", name).strip()
    first = clean.split(" ")[0]
    if any(ch.isdigit() for ch in first) and " " in clean:
        clean = clean.split(" ", 1)[1]
    parts = [x.strip() for x in clean.split(" - ")]
    origin, destination = (parts[0], parts[-1]) if len(parts) > 1 else (clean, clean)
    return origin[:100] or "Depot", destination[:100] or "Depot"


def _route_pool(db: Session, areas: dict[str, int]) -> dict[str, list]:
    """The routes of each area, as (stand, origin, destination). An area with none gets the fictional ones."""
    pool: dict[str, list] = {}
    for area, area_id in areas.items():
        stands = list(db.scalars(select(RouteStand).where(
            RouteStand.kind == PlaceKind.ROUTE, RouteStand.area_id == area_id, RouteStand.is_active).order_by(RouteStand.id)))
        if not stands:
            stands = [_get(db, RouteStand, {"kind": PlaceKind.ROUTE, "name": name}, area_id=area_id)
                      for a, name, _o, _d in ROUTES if a == area]
        pool[area] = [(s, *_ends(s.name)) for s in stands]
    return pool


def _other_buses(db: Session) -> list:
    """Every bus that is not a fictional one and has a permit: (vehicle id, area id, owner id, permit id)."""
    first_permit = select(Permit.vehicle_id, func.min(Permit.id).label("permit_id")).group_by(Permit.vehicle_id).subquery()
    return db.execute(
        select(Vehicle.id, Vehicle.registered_area_id, Vehicle.owner_person_id, first_permit.c.permit_id)
        .join(first_permit, first_permit.c.vehicle_id == Vehicle.id)
        .where(Vehicle.vehicle_type == VehicleType.BUS, ~Vehicle.vehicle_number.like(f"{PLATE}%"))
        .order_by(Vehicle.id)
    ).all()


def plan_other(count: int) -> list[tuple[int, date, int, str]]:
    """(bus index, day, slot, status) for the other buses: every day of the last two weeks, plus some earlier days."""
    rng = random.Random(99)
    dense = [d for d in (END - timedelta(days=n) for n in range(13, -1, -1)) if d >= START]
    days = [START + timedelta(days=n) for n in range(max(0, (END - START).days - 13))]
    earlier = sorted(rng.sample(days, min(IMPORTED_SAMPLE_DAYS, len(days))))
    plan = []
    for day in earlier + dense:
        for bus in range(count):
            if rng.random() < 0.12:
                continue
            for slot in (0, 1):
                if slot == 1 and rng.random() < 0.35:
                    continue
                status = "published"
                if day >= RECENT:
                    status = rng.choice(["published", "published", "published", "approved", "draft"])
                plan.append((bus, day, slot, status))
    return plan


def report(db: Session, trips: list[TripPlan], complaints: list) -> None:
    have = db.scalar(select(func.count()).select_from(Vehicle).where(Vehicle.vehicle_number.like(f"{PLATE}%"))) or 0
    have_trips = db.scalar(
        select(func.count()).select_from(DailyTrip).join(Vehicle, Vehicle.id == DailyTrip.vehicle_id)
        .where(Vehicle.vehicle_number.like(f"{PLATE}%"))
    ) or 0
    have_complaints = db.scalar(select(func.count()).select_from(Complaint).where(Complaint.client_request_id.like(f"{PREFIX}%"))) or 0
    print(f"Period: {START} to {END}")
    print(f"Planned: {len(_buses())} buses, {len(ROUTES)} routes, {len(_people_names())} people, {len(trips)} trips, {len(complaints)} complaints")
    print("  trips by status:", dict(Counter(t.status for t in trips)))
    other = _other_buses(db)
    more = plan_other(len(other))
    print(f"Other buses in the database: {len(other)} with a permit; every route of their area is used")
    print(f"  extra trips for them: {len(more)} over {IMPORTED_SAMPLE_DAYS} sampled days plus the last 14 days")
    print("  by status:", dict(Counter(m[3] for m in more)))
    print("  complaints by target:", dict(Counter(c[2] for c in complaints)))
    print("  complaints by status:", dict(Counter(c[3] for c in complaints)))
    print(f"Already in the database: {have} synthetic buses, {have_trips} synthetic trips, {have_complaints} synthetic complaints")


def _create_imported_trips(db: Session, admin, officer, by_area, drivers, conductors) -> None:
    """Test trips for every other bus, on the routes of its own area, with synthetic crews."""
    other = _other_buses(db)
    area_names = {a.id: a.name for a in db.scalars(select(Area).where(Area.name.in_(AREA_NAMES)))}
    next_slot: dict[str, int] = {}
    rows: list = []
    for vid, aid, oid, pid in other:
        name = area_names.get(aid)
        if name is None or not by_area.get(name):
            rows.append(None)
            continue
        pos = next_slot.get(name, 0)
        next_slot[name] = pos + 1  # buses take the area's routes in turn, so every route is used
        rows.append((vid, name, oid, pid, pos))
    existing = (
        set(db.execute(select(DailyTrip.service_date, DailyTrip.vehicle_id, DailyTrip.departure_time)
                       .where(DailyTrip.vehicle_id.in_([o[0] for o in other]))).all())  # any trip, so demo trips are never clashed with
        if other else set()
    )

    batch: list = []
    created = 0

    def flush_batch() -> None:
        nonlocal created
        if not batch:
            return
        returned = db.execute(
            insert(DailyTrip).returning(DailyTrip.id, DailyTrip.vehicle_id, DailyTrip.service_date, DailyTrip.departure_time),
            [b[0] for b in batch],
        ).all()
        ids = {(r.vehicle_id, r.service_date, r.departure_time): r.id for r in returned}
        db.execute(insert(TripDuty), [
            {**b[1], "trip_id": ids[(b[0]["vehicle_id"], b[0]["service_date"], b[0]["departure_time"])]} for b in batch
        ])
        created += len(batch)
        batch.clear()

    for bus, day, slot, status in plan_other(len(other)):
        row = rows[bus]
        if row is None:
            continue
        vid, name, oid, pid, pos = row
        start, end = TRIP_TIMES[slot]
        if (day, vid, start) in existing:
            continue
        stand, origin, destination = by_area[name][(pos + slot) % len(by_area[name])]
        moment = datetime.combine(day, start, tzinfo=LOCAL)
        verified = status in ("approved", "published")
        batch.append((
            {"service_date": day, "vehicle_id": vid, "permit_id": pid, "route_stand_id": stand.id, "departure_time": start,
             "end_time": end, "origin": origin, "destination": destination, "owner_person_id": oid, "remarks": MARKER,
             "status": DutyRecordStatus(status), "created_by_user_id": officer.id if status == "draft" else admin.id,
             "approved_by_user_id": admin.id if verified else None, "approved_at": moment if verified else None,
             "published_by_user_id": admin.id if status == "published" else None,
             "published_at": moment if status == "published" else None},
            {"driver_person_id": drivers[(bus * 3 + slot) % DRIVERS].id,
             "conductor_person_id": conductors[(bus * 5 + slot) % CONDUCTORS].id,
             "driver_start": start, "driver_end": end, "conductor_start": start, "conductor_end": end,
             "verified_by_user_id": admin.id if verified else None, "verified_at": moment if verified else None},
        ))
        if len(batch) >= 4000:
            flush_batch()
    flush_batch()
    print(f"  trips for the other buses: {created} created")


def _get(db: Session, model, find: dict, **fields):
    row = db.scalar(select(model).filter_by(**find))
    if row is None:
        row = model(**find, **fields)
        db.add(row)
        db.flush()
    return row


def create(db: Session, trips: list[TripPlan], complaints: list) -> None:
    check_environment()
    admin = db.scalar(select(User).where(User.role == UserRole.ADMIN, User.is_active).order_by(User.id))
    officer = db.scalar(select(User).where(User.role == UserRole.L1, User.is_active).order_by(User.id))
    if admin is None or officer is None:
        raise SystemExit("There is no active Admin or Level 1 account. Run `python -m app.scripts.seed` first.")
    areas = {a.name: a.id for a in db.scalars(select(Area).where(Area.name.in_(AREA_NAMES)))}
    if len(areas) != len(AREA_NAMES):
        raise SystemExit("The demo areas are missing. Run `python -m app.scripts.seed` first.")

    people = {n: _get(db, Person, {"full_name": n}, person_type=t, team_label=LABEL) for n, t in _people_names()}
    by_area = _route_pool(db, areas)

    buses = []
    for number, area, owner_n in _buses():
        owner = people[f"Synthetic Owner {owner_n:02d}"]
        vehicle = _get(db, Vehicle, {"vehicle_number": number}, vehicle_type=VehicleType.BUS,
                       registered_area_id=areas[area], owner_person_id=owner.id)
        permit = _get(db, Permit, {"permit_number": f"SYN-P-{number[-4:]}"}, vehicle_id=vehicle.id, holder_person_id=owner.id)
        buses.append((vehicle, permit, area, owner))

    existing = set(db.execute(
        select(DailyTrip.service_date, DailyTrip.vehicle_id, DailyTrip.departure_time)
        .join(Vehicle, Vehicle.id == DailyTrip.vehicle_id).where(Vehicle.vehicle_number.like(f"{PLATE}%"))
    ).all())
    drivers = [people[f"Synthetic Driver {i:02d}"] for i in range(1, DRIVERS + 1)]
    conductors = [people[f"Synthetic Conductor {i:02d}"] for i in range(1, CONDUCTORS + 1)]
    made: dict[tuple, DailyTrip] = {}
    added = 0
    for tp in trips:
        vehicle, permit, area, owner = buses[tp.bus]
        start, end = TRIP_TIMES[tp.slot]
        key = (tp.day, vehicle.id, start)
        if key in existing:
            continue
        route = by_area[area][(tp.bus + tp.slot) % len(by_area[area])]  # (stand, origin, destination)
        moment = datetime.combine(tp.day, start, tzinfo=LOCAL)
        trip = DailyTrip(
            service_date=tp.day, vehicle_id=vehicle.id, permit_id=permit.id, route_stand_id=route[0].id,
            departure_time=start, end_time=end, origin=route[1], destination=route[2], owner_person_id=owner.id,
            remarks=MARKER, status=DutyRecordStatus(tp.status),
            created_by_user_id=officer.id if tp.status == "draft" else admin.id,
        )
        if tp.status in ("approved", "published"):
            trip.approved_by_user_id, trip.approved_at = admin.id, moment
        if tp.status == "published":
            trip.published_by_user_id, trip.published_at = admin.id, moment
        db.add(trip)
        made[(tp.day, tp.bus, tp.slot)] = trip
        added += 1
        if added % 2000 == 0:
            db.flush()
    db.flush()
    for tp in trips:
        trip = made.get((tp.day, tp.bus, tp.slot))
        if trip is None:
            continue
        driver = drivers[(tp.bus * 3 + tp.slot) % DRIVERS]
        conductor = conductors[(tp.bus * 5 + tp.slot) % CONDUCTORS]
        verified = tp.status in ("approved", "published")
        db.add(TripDuty(
            trip_id=trip.id, driver_person_id=driver.id, conductor_person_id=conductor.id,
            driver_start=TRIP_TIMES[tp.slot][0], driver_end=TRIP_TIMES[tp.slot][1],
            conductor_start=TRIP_TIMES[tp.slot][0], conductor_end=TRIP_TIMES[tp.slot][1],
            verified_by_user_id=admin.id if verified else None,
            verified_at=datetime.combine(tp.day, TRIP_TIMES[tp.slot][0], tzinfo=LOCAL) if verified else None,
        ))
    db.flush()
    print(f"  trips: {added} created")

    _create_imported_trips(db, admin, officer, by_area, drivers, conductors)
    _create_complaints(db, officer, buses, made, complaints, people, drivers, conductors)
    db.commit()


def _create_complaints(db, officer, buses, made, complaints, people, drivers, conductors) -> None:
    mediums = list(db.scalars(select(ComplaintMedium).where(ComplaintMedium.is_system.is_(False)).order_by(ComplaintMedium.id)))
    categories = list(db.scalars(select(ComplaintCategory).order_by(ComplaintCategory.id)))
    severities = list(db.scalars(select(Severity).order_by(Severity.rank)))
    targets = {t.code: t for t in db.scalars(select(ComplaintTargetType))}
    if not (mediums and categories and severities and targets):
        raise SystemExit("The complaint lists are empty. Run `python -m app.scripts.seed` first.")
    have = set(db.scalars(select(Complaint.client_request_id).where(Complaint.client_request_id.like(f"{PREFIX}%"))))
    created = 0
    for n, tp, target, status_name in complaints:
        if PREFIX + str(n) in have:
            continue
        trip = made.get((tp.day, tp.bus, tp.slot)) or db.scalar(
            select(DailyTrip).where(DailyTrip.service_date == tp.day, DailyTrip.vehicle_id == buses[tp.bus][0].id,
                                    DailyTrip.departure_time == TRIP_TIMES[tp.slot][0]))
        if trip is None:
            continue
        vehicle, permit, area, owner = buses[tp.bus]
        driver = drivers[(tp.bus * 3 + tp.slot) % DRIVERS]
        conductor = conductors[(tp.bus * 5 + tp.slot) % CONDUCTORS]
        l2 = db.scalar(select(User).where(User.role == UserRole.L2, User.is_active, User.area_id == vehicle.registered_area_id))
        status = ComplaintStatus(status_name)
        if status == ComplaintStatus.FORWARDED and l2 is None:
            status = ComplaintStatus.INCOMPLETE
        when = datetime.combine(tp.day, time(18, 0), tzinfo=LOCAL)
        complaint = Complaint(
            status=status, client_request_id=PREFIX + str(n), entered_by_user_id=officer.id,
            medium_id=mediums[n % len(mediums)].id, complainant_name=f"Synthetic Complainant {n:03d}",
            complaint_date=tp.day, vehicle_id=vehicle.id, area_id=vehicle.registered_area_id,
            route_stand_id=trip.route_stand_id, target_type_id=targets[target].id,
            category_id=categories[n % len(categories)].id, severity_id=severities[n % len(severities)].id,
            subject=f"[SYNTHETIC] {SUBJECTS[n % len(SUBJECTS)]}",
            description="[SYNTHETIC] Generated test complaint. Not a real case.",
        )
        if target == "driver":
            complaint.subject_person_id = driver.id
        elif target == "conductor":
            complaint.subject_person_id = conductor.id
        elif target == "owner":
            complaint.subject_person_id = owner.id
        elif target == "other":
            complaint.subject_person_text = "A person at the stand (synthetic)"
        if status != ComplaintStatus.DRAFT:
            complaint.registered_at = when
            complaint.reference_number = f"TEMP-{PREFIX}{n}"
        if status == ComplaintStatus.INCOMPLETE:
            complaint.paused_since = when
        if status == ComplaintStatus.FORWARDED:
            complaint.forwarded_at, complaint.assigned_l2_user_id = when, l2.id
        db.add(complaint)
        db.flush()
        if complaint.reference_number:
            complaint.reference_number = f"SPRPTA-{tp.day.year}-{complaint.id:06d}"
        db.add(ComplaintDutySnapshot(
            complaint_id=complaint.id, trip_id=trip.id, service_date=trip.service_date, bus_number=vehicle.vehicle_number,
            permit_number=permit.permit_number, route_name=db.get(RouteStand, trip.route_stand_id).name,
            origin=trip.origin, destination=trip.destination, departure_time=trip.departure_time,
            owner_person_id=owner.id, owner_name=owner.full_name, driver_person_id=driver.id, driver_name=driver.full_name,
            conductor_person_id=conductor.id, conductor_name=conductor.full_name, verification_status="Verified",
        ))
        created += 1
    print(f"  complaints: {created} created")


def remove(db: Session) -> None:
    check_environment()
    complaint_ids = list(db.scalars(select(Complaint.id).where(Complaint.client_request_id.like(f"{PREFIX}%"))))
    vehicle_ids = list(db.scalars(select(Vehicle.id).where(Vehicle.vehicle_number.like(f"{PLATE}%"))))
    trip_ids = list(db.scalars(select(DailyTrip.id).where(
        (DailyTrip.remarks == MARKER) | (DailyTrip.vehicle_id.in_(vehicle_ids)))))
    db.execute(delete(ComplaintDutySnapshot).where(ComplaintDutySnapshot.complaint_id.in_(complaint_ids)))
    db.execute(delete(Complaint).where(Complaint.id.in_(complaint_ids)))
    db.execute(delete(TripDuty).where(TripDuty.trip_id.in_(trip_ids)))
    db.execute(delete(DailyTrip).where(DailyTrip.id.in_(trip_ids)))
    db.execute(delete(Permit).where(Permit.vehicle_id.in_(vehicle_ids)))
    db.execute(delete(Vehicle).where(Vehicle.id.in_(vehicle_ids)))
    db.execute(delete(RouteStand).where(RouteStand.name.like("[[]SYNTHETIC]%")))
    db.execute(delete(Person).where(Person.team_label == LABEL))
    db.commit()
    print(f"Removed {len(complaint_ids)} complaints, {len(trip_ids)} trips, {len(vehicle_ids)} buses and the other synthetic records.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirm", action="store_true", help="really write to the database (without it nothing changes)")
    parser.add_argument("--remove", action="store_true", help="delete the synthetic data this script created")
    args = parser.parse_args()
    check_environment()
    print(f"Database: {urlparse(settings.database_url.replace('+psycopg', '')).path.lstrip('/')} (development)\n")
    with SessionLocal() as db:
        if args.remove:
            if not args.confirm:
                print("Would delete the synthetic buses, trips, people and complaints. Add --confirm to do it.")
                return
            return remove(db)
        trips = plan_trips()
        complaints = plan_complaints(trips)
        report(db, trips, complaints)
        if args.confirm:
            print("\nWriting…")
            create(db, trips, complaints)
        else:
            print("\nNothing was written. Add --confirm to create it.")


if __name__ == "__main__":
    main()
