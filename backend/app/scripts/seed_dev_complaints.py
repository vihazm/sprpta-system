"""DEVELOPMENT ONLY: sample complaints for every complaint target, to try Complaint Classification by hand.

    python -m app.scripts.seed_dev_complaints              show what would be created (changes nothing)
    python -m app.scripts.seed_dev_complaints --confirm    create it
    python -m app.scripts.seed_dev_complaints --remove --confirm    delete what this script created

What it creates, all clearly marked so it can never be mistaken for real data:
  - Complaints whose subject starts with "[DEV-TEST]" and whose client_request_id starts with "dev-test-".
  - Fictional people (drivers, conductors, an owner, staff) with team_label "DEV-TEST-DATA".
It writes no audit_log rows and changes no existing record. It uses the demo buses, the L1 and L2 demo accounts and the
published daily records that `app.scripts.seed` creates, so run that first. It is repeatable: a second run finds the
rows it made and adds nothing. It refuses to run unless APP_ENV=development and the database is on this computer.
"""

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import ComplaintStatus, PersonType, RejectionType
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.db.session import SessionLocal
from app.models import (
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

MARKER = "[DEV-TEST]"
REQUEST_PREFIX = "dev-test-"
TEAM_LABEL = "DEV-TEST-DATA"

# Fictional people. The names are made up and match nobody.
PEOPLE = [
    ("Test Driver Anura Demo", PersonType.DRIVER),
    ("Test Driver Kasun Demo", PersonType.DRIVER),
    ("Test Conductor Nuwan Demo", PersonType.CONDUCTOR),
    ("Test Conductor Ishara Demo", PersonType.CONDUCTOR),
    ("Test Owner Pradeep Demo", PersonType.OWNER),
    ("Test Staff Malini Demo", PersonType.SPRPTA_STAFF),
]


@dataclass(frozen=True)
class Sample:
    key: str  # becomes the client_request_id, so a second run recognises it
    target: str  # driver, conductor, owner, bus_service, other, or "" for a complaint not classified yet
    status: str  # draft, incomplete, forwarded, rejected
    accused: str  # verified | registered_owner | directory:<person> | text:<name> | none
    bus: str
    subject: str
    category: int  # index into the category list
    days_ago: int


SAMPLES = [
    # Driver
    Sample("d1", "driver", "forwarded", "verified", "ND-7782", "Reckless overtaking near Elpitiya", 0, 1),
    Sample("d2", "driver", "incomplete", "directory:Test Driver Anura Demo", "ND-7782", "Driver shouted at a passenger", 1, 2),
    Sample("d3", "driver", "draft", "text:the driver of the morning bus", "SP NB-2345", "Bus did not stop at the stand", 2, 0),
    Sample("d4", "driver", "draft", "none", "SP NB-2345", "Speeding on the Galle road", 0, 0),
    # Conductor
    Sample("c1", "conductor", "forwarded", "verified", "SP NB-2345", "No ticket was issued", 3, 1),
    Sample("c2", "conductor", "incomplete", "directory:Test Conductor Nuwan Demo", "ND-7782", "Charged more than the fare", 1, 3),
    Sample("c3", "conductor", "draft", "none", "ND-7782", "Rude to an elderly passenger", 2, 0),
    Sample("c4", "conductor", "rejected", "directory:Test Conductor Ishara Demo", "ND-7782", "Duplicate of an earlier test case", 1, 4),
    # Owner
    Sample("o1", "owner", "forwarded", "registered_owner", "ND-7782", "Bus not kept in a safe condition", 3, 2),
    Sample("o2", "owner", "incomplete", "directory:Test Owner Pradeep Demo", "SP NB-2345", "Owner did not answer earlier complaints", 2, 5),
    Sample("o3", "owner", "draft", "none", "SP NB-2345", "Unregistered extra seats fitted", 0, 0),
    # Bus / transport service
    Sample("b1", "bus_service", "forwarded", "none", "SP NB-2345", "Bus left the stand early", 0, 1),
    Sample("b2", "bus_service", "forwarded", "none", "ND-7782", "The service skipped its last trip", 3, 6),
    Sample("b3", "bus_service", "incomplete", "none", "ND-7782", "Bus very dirty and overcrowded", 2, 2),
    Sample("b4", "bus_service", "draft", "none", "SP NB-2345", "Timetable not followed on the route", 1, 0),
    # Other
    Sample("x1", "other", "forwarded", "text:a person at the stand", "SP NB-2345", "Touts harassing passengers at the stand", 2, 3),
    Sample("x2", "other", "incomplete", "directory:Test Staff Malini Demo", "ND-7782", "Staff member gave wrong information", 3, 4),
    Sample("x3", "other", "draft", "text:unknown", "ND-7782", "Other matter to be classified later", 1, 0),
    # Not classified yet (a draft started before the target was chosen)
    Sample("u1", "", "draft", "none", "ND-7782", "Started on the phone, target not chosen yet", 0, 0),
]


def check_environment() -> None:
    """Refuse to run anywhere but a development database on this computer."""
    if settings.app_env != "development":
        raise SystemExit(f"Refused: APP_ENV is {settings.app_env!r}. This script runs only when APP_ENV=development.")
    host = urlparse(settings.database_url.replace("+psycopg", "")).hostname
    if host not in ("localhost", "127.0.0.1", "::1"):
        raise SystemExit(f"Refused: the database host is {host!r}, not this computer.")


def _people(db: Session) -> dict[str, Person]:
    found = {p.full_name: p for p in db.scalars(select(Person).where(Person.team_label == TEAM_LABEL))}
    for name, person_type in PEOPLE:
        if name not in found:
            found[name] = Person(full_name=name, person_type=person_type, team_label=TEAM_LABEL)
            db.add(found[name])
    db.flush()
    return found


def _verified_duty(db: Session, bus: str, role: str):
    """A published daily record of this bus with a verified driver or conductor, and that person."""
    row = db.execute(
        select(DailyTrip, TripDuty)
        .join(TripDuty, TripDuty.trip_id == DailyTrip.id)
        .join(Vehicle, Vehicle.id == DailyTrip.vehicle_id)
        .where(Vehicle.vehicle_number == bus, DailyTrip.status == "published")
        .where((TripDuty.driver_person_id if role == "driver" else TripDuty.conductor_person_id).is_not(None))
        .order_by(DailyTrip.service_date.desc(), DailyTrip.departure_time)
    ).first()
    return row


def plan(db: Session) -> list[tuple[Sample, str]]:
    """Each sample with 'new', 'exists', or why it will be skipped."""
    existing = set(db.scalars(select(Complaint.client_request_id).where(Complaint.client_request_id.like(f"{REQUEST_PREFIX}%"))))
    result = []
    for sample in SAMPLES:
        if REQUEST_PREFIX + sample.key in existing:
            result.append((sample, "exists"))
        elif db.scalar(select(Vehicle.id).where(Vehicle.vehicle_number == sample.bus)) is None:
            result.append((sample, f"skipped: bus {sample.bus} is not in the database"))
        elif sample.accused == "verified" and _verified_duty(db, sample.bus, sample.target) is None:
            result.append((sample, f"skipped: no published daily record with a verified {sample.target} for {sample.bus}"))
        else:
            result.append((sample, "new"))
    return result


def report(rows: list[tuple[Sample, str]]) -> None:
    print(f"{'key':4} {'target':12} {'status':11} {'accused':40} result")
    for sample, result in rows:
        print(f"{sample.key:4} {sample.target or '(none)':12} {sample.status:11} {sample.accused[:38]:40} {result}")
    new = [s for s, r in rows if r == "new"]
    print()
    print("Would create:", len(new), "complaints")
    by_target = Counter(s.target or "unclassified" for s in new)
    print("  by target:", ", ".join(f"{k} {v}" for k, v in sorted(by_target.items())) or "none")
    by_status = Counter(s.status for s in new)
    print("  by status:", ", ".join(f"{k} {v}" for k, v in sorted(by_status.items())) or "none")
    print("  fictional people:", len(PEOPLE), "(only those not already there)")


def create(db: Session) -> None:
    check_environment()
    officer = db.scalar(select(User).where(User.role == UserRole.L1, User.is_active).order_by(User.id))
    if officer is None:
        raise SystemExit("There is no active Level 1 account. Run `python -m app.scripts.seed` first.")
    mediums = list(db.scalars(select(ComplaintMedium).where(ComplaintMedium.is_system.is_(False)).order_by(ComplaintMedium.id)))
    categories = list(db.scalars(select(ComplaintCategory).order_by(ComplaintCategory.id)))
    severities = list(db.scalars(select(Severity).order_by(Severity.rank)))
    targets = {t.code: t for t in db.scalars(select(ComplaintTargetType))}
    if not (mediums and categories and severities and targets):
        raise SystemExit("The complaint lists are empty. Run `python -m app.scripts.seed` first.")
    people = _people(db)
    now = datetime.now(LOCAL)

    for sample, result in plan(db):
        if result != "new":
            print(f"  {sample.key}: {result}")
            continue
        vehicle = db.scalar(select(Vehicle).where(Vehicle.vehicle_number == sample.bus))
        when = now - timedelta(days=sample.days_ago)
        status = ComplaintStatus(sample.status)
        l2 = db.scalar(select(User).where(User.role == UserRole.L2, User.is_active, User.area_id == vehicle.registered_area_id))
        if status == ComplaintStatus.FORWARDED and l2 is None:
            status = ComplaintStatus.INCOMPLETE  # no area officer to hand it to
            print(f"  {sample.key}: no Level 2 officer for that area, saved as incomplete instead")

        complaint = Complaint(
            status=status,
            client_request_id=REQUEST_PREFIX + sample.key,
            entered_by_user_id=officer.id,
            medium_id=mediums[sample.days_ago % len(mediums)].id,
            complainant_name=f"Test Complainant {sample.key.upper()}",
            complaint_date=when.date(),
            vehicle_id=vehicle.id,
            area_id=vehicle.registered_area_id,
            target_type_id=targets[sample.target].id if sample.target else None,
            category_id=categories[sample.category % len(categories)].id,
            severity_id=severities[sample.category % len(severities)].id,
            subject=f"{MARKER} {sample.subject}",
            description=f"{MARKER} Sample complaint for trying Complaint Classification. Not a real case.",
        )
        snapshot_trip = None
        if sample.accused == "verified":
            snapshot_trip, duty = _verified_duty(db, sample.bus, sample.target)
            complaint.subject_person_id = duty.driver_person_id if sample.target == "driver" else duty.conductor_person_id
        elif sample.accused == "registered_owner":
            complaint.subject_person_id = vehicle.owner_person_id
        elif sample.accused.startswith("directory:"):
            complaint.subject_person_id = people[sample.accused.split(":", 1)[1]].id
        elif sample.accused.startswith("text:"):
            complaint.subject_person_text = sample.accused.split(":", 1)[1]
        if status != ComplaintStatus.DRAFT:
            complaint.registered_at = when
        if status == ComplaintStatus.INCOMPLETE:
            complaint.paused_since = when
        if status == ComplaintStatus.FORWARDED:
            complaint.forwarded_at = when
            complaint.assigned_l2_user_id = l2.id
        if status == ComplaintStatus.REJECTED:
            complaint.rejection_type = RejectionType.INVALID
            complaint.rejection_reason = f"{MARKER} Sample rejection."
        needs_reference = status not in (ComplaintStatus.DRAFT, ComplaintStatus.REJECTED)
        if needs_reference:
            complaint.reference_number = f"TEMP-{REQUEST_PREFIX}{sample.key}"  # the table requires one at insert time
        db.add(complaint)
        db.flush()
        if needs_reference:
            complaint.reference_number = f"SPRPTA-{when.year}-{complaint.id:06d}"  # as the app issues it, from the row id
        if snapshot_trip is not None:
            duty = db.scalar(select(TripDuty).where(TripDuty.trip_id == snapshot_trip.id))
            names = {p.id: p.full_name for p in db.scalars(select(Person).where(Person.id.in_([duty.driver_person_id, duty.conductor_person_id])))}
            permit = db.get(Permit, snapshot_trip.permit_id)
            route = db.get(RouteStand, snapshot_trip.route_stand_id)
            db.add(ComplaintDutySnapshot(
                complaint_id=complaint.id, trip_id=snapshot_trip.id, service_date=snapshot_trip.service_date,
                bus_number=sample.bus, permit_number=permit.permit_number, route_name=route.name,
                origin=snapshot_trip.origin, destination=snapshot_trip.destination, departure_time=snapshot_trip.departure_time,
                owner_person_id=vehicle.owner_person_id,
                owner_name=names.get(vehicle.owner_person_id) or (db.get(Person, vehicle.owner_person_id).full_name if vehicle.owner_person_id else None),
                driver_person_id=duty.driver_person_id, driver_name=names.get(duty.driver_person_id),
                conductor_person_id=duty.conductor_person_id, conductor_name=names.get(duty.conductor_person_id),
                verification_status="Verified",
            ))
        print(f"  {sample.key}: created {complaint.reference_number or '(draft)'}")
    db.commit()


def remove(db: Session) -> None:
    check_environment()
    ids = list(db.scalars(select(Complaint.id).where(Complaint.client_request_id.like(f"{REQUEST_PREFIX}%"))))
    db.execute(delete(ComplaintDutySnapshot).where(ComplaintDutySnapshot.complaint_id.in_(ids)))
    db.execute(delete(Complaint).where(Complaint.id.in_(ids)))
    people = db.execute(delete(Person).where(Person.team_label == TEAM_LABEL))
    db.commit()
    print(f"Removed {len(ids)} sample complaints and {people.rowcount} sample people.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirm", action="store_true", help="really write to the database (without it nothing changes)")
    parser.add_argument("--remove", action="store_true", help="delete the sample data this script created")
    args = parser.parse_args()
    check_environment()
    print(f"Database: {urlparse(settings.database_url.replace('+psycopg', '')).path.lstrip('/')} (development)\n")
    with SessionLocal() as db:
        if args.remove:
            if not args.confirm:
                count = db.scalar(select(__import__("sqlalchemy").func.count()).select_from(Complaint).where(Complaint.client_request_id.like(f"{REQUEST_PREFIX}%")))
                print(f"Would remove {count} sample complaints and the sample people. Add --confirm to do it.")
                return
            return remove(db)
        report(plan(db))
        if args.confirm:
            print("\nWriting…")
            create(db)
        else:
            print("\nNothing was written. Add --confirm to create it.")


if __name__ == "__main__":
    main()
