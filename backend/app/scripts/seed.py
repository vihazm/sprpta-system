"""Seed reference data and the first accounts. Safe to run repeatedly.

    cd backend
    .venv\\Scripts\\python -m app.scripts.seed

- Always: the three areas (DB doc 5.7).
- Development only (APP_ENV=development): one demo account per role, so every
  role's redirect can be tried. Logins are emails, as the documents require.
  Also the lists the Level 1 complaint form needs (mediums, categories,
  severities, a few demo vehicles, permits, owners and routes), and published
  daily duty records for the Bus & Permit Lookup (yesterday and today).
- Production: one admin from ADMIN_LOGIN / ADMIN_PASSWORD / ADMIN_NAME (set in
  the environment, never committed). The password is not defined by the
  documents ([OPEN] in the UI Flow doc), so it comes from the environment.

The development passwords below are public demo values. To give an account a
different one without committing it, set SEED_PASSWORD_<NAME> in backend/.env,
where <NAME> is the part of the login before the "@" in capitals, for example
SEED_PASSWORD_SHAMILA_AD_MATARA=...
"""

import os
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import DutyRecordStatus, PersonType, PlaceKind, VehicleType
from app.core.identifiers import normalise_identifier
from app.core.roles import UserRole
from app.core.security import hash_password
from app.core.timezone import LOCAL
from app.db.session import SessionLocal
from app.models import (
    Area,
    ComplainantAccount,
    ComplaintCategory,
    ComplaintMedium,
    DailyTrip,
    Permit,
    Person,
    RouteStand,
    Severity,
    TripDuty,
    User,
    Vehicle,
)

AREAS = ["Galle", "Matara", "Hambantota"]

# DEVELOPMENT ONLY. These credentials are public in the repository; they are
# never created when APP_ENV is not "development".
DEV_STAFF = [
    # (full name, login, role, area, password)
    ("Test Chairman", "test_chairman@sprpta.test", UserRole.L3, None, "chairman123"),
    # One active L2 officer per area, so forwarding by area finds exactly one.
    ("Gihan Samaraweera", "gihan_ad_galle@sprpta.test", UserRole.L2, "Galle", "ad_galle123"),
    ("Shamila Liyanarachchi", "shamila_ad_matara@sprpta.test", UserRole.L2, "Matara", "ad_matara123"),
    ("Kavindya Sewwandi", "kavindya_ad_hambantota@sprpta.test", UserRole.L2, "Hambantota", "ad_hambantota123"),
    ("Test Office Staff", "test_office@sprpta.test", UserRole.L1, None, "office123"),
    ("System Admin", "system_admin@sprpta.test", UserRole.ADMIN, None, "admin123"),
    ("Test Ground Staff", "test_groundstaff@sprpta.test", UserRole.IMPLEMENTING_STAFF, None, "groundstaff123"),
]
DEV_COMPLAINANTS = [
    # (display name, email, password)
    ("Test Client", "test_client1@sprpta.test", "client1abc"),
]


# DEVELOPMENT ONLY: the lists the Level 1 complaint form looks things up in, until Admin's master data exists.
MEDIUMS = ["WhatsApp", "Email", "SMS", "Letter", "Phone call", "Walk-in"]
CATEGORIES = ["Staff behaviour", "Overcharging", "Reckless driving", "Timetable or route"]
SEVERITIES = [
    # (name, rank, forward / decide / close days, rating weight): the proposed defaults of DB doc 2.10
    ("Critical", 1, 0, 1, 3, 8),
    ("High", 2, 1, 3, 7, 4),
    ("Medium", 3, 2, 7, 14, 2),
    ("Low", 4, 3, 14, 30, 1),
]
DEV_VEHICLES = [
    # (area, vehicle number, type, owner, permit number, route or stand)
    ("Galle", "SP NB-2345", VehicleType.BUS, "Nimal Perera", "GL-BP-0101", "Galle - Matara (route 2)"),
    ("Galle", "SP QA-1234", VehicleType.TRISHAW, "Sunil Jayasinghe", "GL-TP-0207", "Galle Fort stand"),
    ("Matara", "SP NC-4521", VehicleType.BUS, "Kamal Silva", "MT-BP-0112", "Matara - Colombo (route 2)"),
    ("Hambantota", "SP ND-7788", VehicleType.BUS, "Ruwan Fernando", "HB-BP-0123", "Hambantota - Tangalle (route 31)"),
    # The bus the sample trips and sample complaints use; the client's workbook has it too, and then it is matched.
    ("Galle", "ND-7782", VehicleType.BUS, "Piyal Gunasekara", "GL-BP-0102", "24/1 Avithtawa - Elpitiya"),
]
DEV_PEOPLE = [
    # (name, type)
    ("Saman Kumara", PersonType.DRIVER),
    ("Chaminda Rathnayake", PersonType.CONDUCTOR),
    ("Dilani Wickramasinghe", PersonType.SPRPTA_STAFF),
]


def _get_or_create(db: Session, model, find: dict, **fields):
    row = db.scalar(select(model).filter_by(**find))
    if row is None:
        row = model(**find, **fields)
        db.add(row)
        db.flush()
        print(f"  created {find}")
    return row


def _seed_complaint_lookups(db: Session, areas: dict[str, int]) -> None:
    print("Complaint form lists (development only)")
    for name in MEDIUMS:
        _get_or_create(db, ComplaintMedium, {"name": name})
    _get_or_create(db, ComplaintMedium, {"name": "Portal"}, is_system=True)
    for name in CATEGORIES:
        _get_or_create(db, ComplaintCategory, {"name": name})
    for name, rank, forward_days, decide_days, close_days, weight in SEVERITIES:
        _get_or_create(
            db, Severity, {"name": name},
            rank=rank, forward_days=forward_days, decide_days=decide_days, close_days=close_days, rating_weight=weight,
        )
    for name, person_type in DEV_PEOPLE:
        _get_or_create(db, Person, {"full_name": name}, person_type=person_type)
    for area, number, vehicle_type, owner_name, permit_number, place in DEV_VEHICLES:
        owner = _get_or_create(db, Person, {"full_name": owner_name}, person_type=PersonType.OWNER)
        vehicle = _get_or_create(
            db, Vehicle, {"vehicle_number": number},
            vehicle_type=vehicle_type, registered_area_id=areas[area], owner_person_id=owner.id,
        )
        kind = PlaceKind.STAND if "stand" in place else PlaceKind.ROUTE
        route = _get_or_create(db, RouteStand, {"kind": kind, "name": place, "area_id": areas[area]})
        # The permit records its route (as the client's workbook import does), so the synthetic generator can run on
        # these demo buses alone.
        permit = _get_or_create(
            db, Permit, {"permit_number": permit_number},
            vehicle_id=vehicle.id, holder_person_id=owner.id, route_stand_id=route.id,
        )
        if permit.route_stand_id is None:
            permit.route_stand_id = route.id


# DEVELOPMENT ONLY: published daily records for the Bus & Permit Lookup, for yesterday and today.
# (bus number, route, origin, destination, departure time, driver, conductor): a missing person stays Unavailable.
DEV_TRIPS = [
    ("SP NB-2345", "Galle - Matara (route 2)", "Galle", "Matara", time(6, 30), "Saman Kumara", "Chaminda Rathnayake"),
    ("SP NB-2345", "Galle - Matara (route 2)", "Galle", "Matara", time(14, 15), "Saman Kumara", None),
    ("ND-7782", "24/1 Avithtawa - Elpitiya", "Avithtawa", "Elpitiya", time(7, 0), "Saman Kumara", "Chaminda Rathnayake"),
    ("ND-7782", "24/1 Avithtawa - Elpitiya", "Avithtawa", "Elpitiya", time(15, 30), None, None),
]


def _seed_duty_records(db: Session) -> None:
    """Needs the demo vehicles; the buses from the client's workbook are used when they have been imported."""
    print("Daily duty records (development only)")
    admin = db.scalar(select(User).where(User.role == UserRole.ADMIN))
    today = datetime.now(LOCAL).date()
    now = datetime.now(LOCAL)
    for number, route_name, origin, destination, departure, driver_name, conductor_name in DEV_TRIPS:
        vehicle = db.scalar(select(Vehicle).where(Vehicle.vehicle_number == number))
        route = db.scalar(select(RouteStand).where(RouteStand.name == route_name))
        permit = db.scalar(select(Permit).where(Permit.vehicle_id == vehicle.id)) if vehicle else None
        if admin is None or vehicle is None or route is None or permit is None:
            print(f"  skipped {number} {departure:%H:%M}: the vehicle, its permit or the route is not in the database")
            continue
        for day in (today - timedelta(days=1), today):
            if db.scalar(select(DailyTrip.id).where(
                DailyTrip.service_date == day, DailyTrip.vehicle_id == vehicle.id, DailyTrip.departure_time == departure
            )):
                continue
            trip = DailyTrip(
                service_date=day, vehicle_id=vehicle.id, permit_id=permit.id, route_stand_id=route.id,
                departure_time=departure, origin=origin, destination=destination, status=DutyRecordStatus.PUBLISHED,
                created_by_user_id=admin.id, approved_by_user_id=admin.id, approved_at=now,
                published_by_user_id=admin.id, published_at=now,
            )
            db.add(trip)
            db.flush()
            driver = db.scalar(select(Person).where(Person.full_name == driver_name)) if driver_name else None
            conductor = db.scalar(select(Person).where(Person.full_name == conductor_name)) if conductor_name else None
            if driver or conductor:
                db.add(TripDuty(
                    trip_id=trip.id, driver_person_id=driver.id if driver else None,
                    conductor_person_id=conductor.id if conductor else None,
                    verified_by_user_id=admin.id, verified_at=now,
                ))
            print(f"  created {number} {departure:%H:%M} on {day}")


def _dev_password(login: str, demo_password: str) -> str:
    """The SEED_PASSWORD_<NAME> override from the environment or backend/.env, else the demo password."""
    key = "SEED_PASSWORD_" + login.split("@")[0].upper()
    env_file = Path(__file__).resolve().parents[2] / ".env"
    return os.environ.get(key) or dotenv_values(env_file).get(key) or demo_password


def _area_ids(db: Session) -> dict[str, int]:
    ids: dict[str, int] = {}
    for name in AREAS:
        area = db.scalar(select(Area).where(Area.name == name))
        if area is None:
            area = Area(name=name)
            db.add(area)
            db.flush()
            print(f"  created area {name}")
        ids[name] = area.id
    return ids


def _ensure_staff(db: Session, name: str, login: str, role: UserRole, area_id: int | None, password: str) -> None:
    parsed = normalise_identifier(login)
    if parsed is None:
        raise SystemExit(f"Not a valid email or Sri Lankan mobile number: {login!r}")
    login = parsed[1]
    if db.scalar(select(User).where(User.login == login)) is not None:
        print(f"  exists  {login} ({role.value})")
        return
    db.add(User(full_name=name, login=login, password_hash=hash_password(password), role=role, area_id=area_id))
    print(f"  created {login} ({role.value})")


def main() -> None:
    with SessionLocal() as db:
        print("Areas")
        areas = _area_ids(db)

        if settings.is_development:
            print("Development accounts")
            for name, login, role, area, password in DEV_STAFF:
                _ensure_staff(db, name, login, role, areas[area] if area else None, _dev_password(login, password))
            for name, email, password in DEV_COMPLAINANTS:
                if db.scalar(select(ComplainantAccount).where(ComplainantAccount.email == email)) is None:
                    db.add(
                        ComplainantAccount(
                            display_name=name,
                            email=email,
                            password_hash=hash_password(password),
                            verified_at=datetime.now(UTC),
                        )
                    )
                    print(f"  created {email} (cp)")
                else:
                    print(f"  exists  {email} (cp)")
            _seed_complaint_lookups(db, areas)
            db.flush()
            _seed_duty_records(db)
        else:
            login, password = os.environ.get("ADMIN_LOGIN"), os.environ.get("ADMIN_PASSWORD")
            if not login or not password:
                raise SystemExit("Set ADMIN_LOGIN and ADMIN_PASSWORD to create the first admin.")
            print("Administrator")
            _ensure_staff(db, os.environ.get("ADMIN_NAME", "System Administrator"), login,
                          UserRole.ADMIN, None, password)
        db.commit()
    print("Done.")


if __name__ == "__main__":
    main()
