"""Writing a planned synthetic dataset to the database, in batches. Restartable: whatever already exists is skipped.

Everything written carries the batch's synthetic_batch_id. No audit_log rows are written (it is append-only, so they
could never be removed); the simulated complaint history goes to synthetic_complaint_events instead.
"""

import random
from collections import defaultdict
from datetime import datetime, time, timedelta

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.enums import ComplaintStatus, DuplicateLinkType, DutyRecordStatus, PersonType, RejectionType
from app.core.roles import UserRole
from app.core.security import hash_password
from app.core.timezone import LOCAL
from app.models import (
    Area,
    BusNonOperation,
    Complaint,
    ComplaintCategory,
    ComplaintDutySnapshot,
    ComplaintMedium,
    ComplaintTargetType,
    DailyTrip,
    DuplicateCheck,
    OwnerAssignment,
    Permit,
    Person,
    RouteAuthorization,
    RouteStand,
    Severity,
    SyntheticBatch,
    SyntheticComplaintEvent,
    TripDuty,
    User,
    Vehicle,
)
from app.scripts.seed_dev_complaints import check_environment
from app.synthetic.pipeline import Plan

SYNTHETIC_PASSWORD = "synthetic-dev-only"  # the fictional officers exist only in development databases
TRIP_BATCH = 4000
COMPLAINT_BATCH = 400
REMARKS = "Synthetic test data"


def _t(minutes: int | None) -> time | None:
    return None if minutes is None else time(minutes // 60, minutes % 60)


def get_batch(db: Session, plan: Plan) -> SyntheticBatch:
    batch = db.scalar(select(SyntheticBatch).where(SyntheticBatch.name == plan.cfg.batch_name))
    if batch is None:
        batch = SyntheticBatch(name=plan.cfg.batch_name, scale=plan.cfg.scale, seed=plan.cfg.seed, config=plan.cfg.raw)
        db.add(batch)
        db.flush()
    return batch


def _ensure_users(db: Session, plan: Plan, area_names: dict[str, int]) -> tuple[list[int], dict[str, int], int]:
    """(Level 1 officer ids with the demo officer first, a Level 2 officer id per office, an Admin id)."""
    general = plan.cfg.section("general")
    admin = db.scalar(select(User).where(User.login == general["admin_login"])) or db.scalar(
        select(User).where(User.role == UserRole.ADMIN, User.is_active).order_by(User.id))
    if admin is None:
        raise SystemExit("There is no Admin account. Run `python -m app.scripts.seed` first.")
    demo = db.scalar(select(User).where(User.login == general["demo_officer_login"])) or db.scalar(
        select(User).where(User.role == UserRole.L1, User.is_active).order_by(User.id))
    if demo is None:
        raise SystemExit("There is no Level 1 account. Run `python -m app.scripts.seed` first.")
    officers = [demo.id]
    for i in range(1, int(general["synthetic_officers"]) + 1):
        login = f"syn_l1_{i}@sprpta.test"
        user = db.scalar(select(User).where(User.login == login))
        if user is None:
            user = User(full_name=f"Synthetic Officer {i}", login=login, password_hash=hash_password(SYNTHETIC_PASSWORD), role=UserRole.L1)
            db.add(user)
            db.flush()
        officers.append(user.id)
    level2 = {}
    for name, area_id in area_names.items():
        user = db.scalar(select(User).where(User.role == UserRole.L2, User.is_active, User.area_id == area_id).order_by(User.id))
        if user is None:
            login = f"syn_l2_{name.lower()}@sprpta.test"
            user = db.scalar(select(User).where(User.login == login))
            if user is None:
                user = User(full_name=f"Synthetic Area Officer {name}", login=login,
                            password_hash=hash_password(SYNTHETIC_PASSWORD), role=UserRole.L2, area_id=area_id)
                db.add(user)
                db.flush()
        level2[name] = user.id
    return officers, level2, admin.id


def _people(db: Session, plan: Plan, batch: SyntheticBatch) -> tuple[dict[int, int], dict[int, int], dict[int, int]]:
    """Fictional owners, drivers and conductors. team_label records which one each is, so a restart finds it."""
    existing = {p.team_label: p.id for p in db.scalars(select(Person).where(Person.synthetic_batch_id == batch.id))}
    maps: list[dict[int, int]] = []
    for kind, ptype, names in (("owner", PersonType.OWNER, plan.world.owners),
                               ("driver", PersonType.DRIVER, [s.name for s in plan.world.drivers]),
                               ("conductor", PersonType.CONDUCTOR, [s.name for s in plan.world.conductors])):
        mapping: dict[int, int] = {}
        fresh = []
        for index, name in enumerate(names):
            label = f"SYN:{batch.id}:{kind}:{index}"
            if label in existing:
                mapping[index] = existing[label]
            else:
                person = Person(full_name=name, person_type=ptype, team_label=label, synthetic_batch_id=batch.id)
                fresh.append((index, person))
        db.add_all(p for _i, p in fresh)
        db.flush()
        mapping.update({i: p.id for i, p in fresh})
        maps.append(mapping)
    return maps[0], maps[1], maps[2]


def seed(db: Session, plan: Plan, log=print) -> dict:
    check_environment()  # development databases on this computer only, whoever calls this
    area_ids = {a.name: a.id for a in db.scalars(select(Area))}
    batch = get_batch(db, plan)
    officers, level2, admin_id = _ensure_users(db, plan, area_ids)
    owner_ids, driver_ids, conductor_ids = _people(db, plan, batch)
    world = plan.world
    buses = {b.id: b for b in plan.network.buses}
    db.commit()
    log(f"  people: {len(owner_ids)} owners, {len(driver_ids)} drivers, {len(conductor_ids)} conductors")

    # ---- ownership, non-operating periods, route authorizations
    have = set(db.execute(select(OwnerAssignment.vehicle_id, OwnerAssignment.valid_from)
                          .where(OwnerAssignment.synthetic_batch_id == batch.id)).all())
    rows = []
    now = datetime.now(LOCAL)
    for bus_id, owner, start, end in world.ownership:
        if (bus_id, start) not in have:
            rows.append({"vehicle_id": bus_id, "owner_person_id": owner_ids[owner], "valid_from": start, "valid_to": end,
                         "status": DutyRecordStatus.PUBLISHED, "created_by_user_id": admin_id, "approved_by_user_id": admin_id,
                         "approved_at": now, "published_by_user_id": admin_id, "published_at": now,
                         "synthetic_batch_id": batch.id})
    for i in range(0, len(rows), 2000):
        db.execute(insert(OwnerAssignment), rows[i:i + 2000])
    have_ops = set(db.execute(select(BusNonOperation.vehicle_id, BusNonOperation.start_date, BusNonOperation.reason)
                              .where(BusNonOperation.synthetic_batch_id == batch.id)).all())
    ops = [{"vehicle_id": b, "start_date": s, "end_date": e, "reason": r, "note": "Synthetic test data",
            "synthetic_batch_id": batch.id} for b, s, e, r in world.non_ops if (b, s, r) not in have_ops]
    for i in range(0, len(ops), 4000):
        db.execute(insert(BusNonOperation), ops[i:i + 4000])
    have_auth = set(db.execute(select(RouteAuthorization.vehicle_id, RouteAuthorization.valid_from)
                               .where(RouteAuthorization.synthetic_batch_id == batch.id)).all())
    auths = [{"vehicle_id": b, "route_stand_id": r, "valid_from": s, "valid_to": e, "reason": why,
              "synthetic_batch_id": batch.id} for b, r, s, e, why in world.auths if (b, s) not in have_auth]
    if auths:
        db.execute(insert(RouteAuthorization), auths)
    db.commit()
    log(f"  ownership {len(rows)}, non-operating periods {len(ops)}, route authorizations {len(auths)} written")

    # ---- trips and their duty rows, office by office
    by_area: dict[str, list] = defaultdict(list)
    for trip in world.trips:
        by_area[buses[trip.bus_id].area].append(trip)
    trip_ids: dict[tuple, int] = {}
    created = 0
    for area, trips in sorted(by_area.items()):
        vehicle_ids = {t.bus_id for t in trips}
        existing = {(r.vehicle_id, r.service_date, r.departure_time): r.id for r in db.execute(
            select(DailyTrip.id, DailyTrip.vehicle_id, DailyTrip.service_date, DailyTrip.departure_time)
            .where(DailyTrip.vehicle_id.in_(vehicle_ids)))}
        batch_rows: list[tuple[dict, dict | None]] = []

        def flush_rows() -> None:
            nonlocal created
            if not batch_rows:
                return
            returned = db.execute(
                insert(DailyTrip).returning(DailyTrip.id, DailyTrip.vehicle_id, DailyTrip.service_date, DailyTrip.departure_time),
                [r[0] for r in batch_rows],
            ).all()
            ids = {(r.vehicle_id, r.service_date, r.departure_time): r.id for r in returned}
            duties = [{**d, "trip_id": ids[(r["vehicle_id"], r["service_date"], r["departure_time"])]}
                      for r, d in batch_rows if d is not None]
            if duties:
                db.execute(insert(TripDuty), duties)
            for key, trip_id in ids.items():
                existing[key] = trip_id
            created += len(batch_rows)
            db.commit()
            batch_rows.clear()

        for t in trips:
            key = (t.bus_id, t.day, _t(t.dep))
            if key in existing:
                continue
            bus = buses[t.bus_id]
            route = plan.network.routes[t.route_id]
            last_week = t.day >= plan.cfg.end - timedelta(days=6)
            status = "published"
            if last_week:  # the newest records are still being processed, so Admin has something to do
                status = random.Random(f"{t.bus_id}:{t.day}:{t.dep}").choice(
                    ["published", "published", "published", "approved", "draft"])
            moment = datetime.combine(t.day, _t(t.dep), LOCAL)
            verified = status in ("approved", "published")
            row = {
                "service_date": t.day, "vehicle_id": t.bus_id, "permit_id": bus.permit_id, "route_stand_id": route.id,
                "departure_time": _t(t.dep), "end_time": _t(t.arr), "origin": t.origin, "destination": t.destination,
                "owner_person_id": owner_ids[t.owner] if t.owner is not None else None, "remarks": REMARKS,
                "status": DutyRecordStatus(status), "trip_status": t.status, "direction": t.direction,
                "actual_departure": _t(t.a_dep), "actual_arrival": _t(t.a_arr), "synthetic_batch_id": batch.id,
                "created_by_user_id": officers[1] if status == "draft" else admin_id,
                "approved_by_user_id": admin_id if verified else None, "approved_at": moment if verified else None,
                "published_by_user_id": admin_id if status == "published" else None,
                "published_at": moment if status == "published" else None,
            }
            duty = None
            if t.driver is not None:
                duty = {"driver_person_id": driver_ids[t.driver], "conductor_person_id": conductor_ids[t.conductor],
                        "driver_start": _t(t.d_start), "driver_end": _t(t.d_end),
                        "conductor_start": _t(t.c_start), "conductor_end": _t(t.c_end),
                        "verified_by_user_id": admin_id if verified else None, "verified_at": moment if verified else None}
            batch_rows.append((row, duty))
            if len(batch_rows) >= TRIP_BATCH:
                flush_rows()
        flush_rows()
        trip_ids.update(existing)
        log(f"  trips: {area} done ({created} written so far)")

    _complaints(db, plan, batch, officers, level2, admin_id, owner_ids, driver_ids, conductor_ids, trip_ids, area_ids, log)
    return {"trips_written": created}


def _complaints(db, plan, batch, officers, level2, admin_id, owner_ids, driver_ids, conductor_ids, trip_ids, area_ids, log):
    world, network = plan.world, plan.network
    buses = {b.id: b for b in network.buses}
    targets = {t.code: t.id for t in db.scalars(select(ComplaintTargetType))}
    categories = list(db.scalars(select(ComplaintCategory).where(ComplaintCategory.is_active).order_by(ComplaintCategory.id)))
    mediums = list(db.scalars(select(ComplaintMedium).where(ComplaintMedium.is_system.is_(False)).order_by(ComplaintMedium.id)))
    severities = list(db.scalars(select(Severity).order_by(Severity.rank)))
    existing = {c.client_request_id: c.id for c in db.execute(
        select(Complaint.client_request_id, Complaint.id).where(Complaint.synthetic_batch_id == batch.id))
        if c.client_request_id}
    ids: dict[int, int] = {}
    key = lambda n: f"{batch.name}-{n:06d}"  # noqa: E731
    ids.update({int(k.rsplit("-", 1)[1]): v for k, v in existing.items()})
    pending: list = []
    written = 0

    def finish() -> None:
        nonlocal written
        db.commit()
        written += len(pending)
        pending.clear()

    permit_numbers = dict(db.execute(select(Permit.id, Permit.permit_number)).all())
    for c in plan.complaints:
        if c.n in ids:
            continue
        if c.duplicate_of is not None and c.duplicate_of not in ids:  # the earlier case must be stored first
            _finish_batch(db, pending, ids, batch, officers, owner_ids, driver_ids, conductor_ids, trip_ids, world, network, permit_numbers)
            finish()
        bus = buses.get(c.bus_id) if c.bus_id is not None else None
        trip = world.trips[c.trip_index] if c.trip_index is not None else None
        status = ComplaintStatus(c.status)
        first_non_draft = next((w for s, w in c.path if s != "draft"), None)
        when = {s: w for s, w in c.path}
        area_name = bus.area if bus else None
        l2 = level2.get(area_name) if area_name else None
        subject_person = None
        if c.accused_kind == "driver" and c.accused_index is not None:
            subject_person = driver_ids[c.accused_index]
        elif c.accused_kind == "conductor" and c.accused_index is not None:
            subject_person = conductor_ids[c.accused_index]
        elif c.accused_kind == "owner" and c.accused_index is not None:
            subject_person = owner_ids[c.accused_index]
        anonymous = c.name is None
        row = Complaint(
            status=status, entered_by_user_id=officers[c.officer], medium_id=mediums[c.medium % len(mediums)].id,
            is_anonymous=anonymous, complainant_name=c.name, contact_phone=c.phone, contact_email=c.email,
            complaint_date=c.day, incident_time=time(c.incident_time // 60, c.incident_time % 60) if c.incident_time else None,
            incident_location=c.location, target_type_id=targets[c.target], subject=c.subject, description=c.description,
            category_id=categories[c.category % len(categories)].id, severity_id=severities[min(c.severity, len(severities) - 1)].id,
            subject_person_id=subject_person, subject_person_text=c.accused_text if subject_person is None else None,
            vehicle_number_entered=c.reported_bus, vehicle_id=bus.id if bus else None, permit_id=bus.permit_id if bus else None,
            owner_person_id=owner_ids[trip.owner] if trip is not None and trip.owner is not None else None,
            route_stand_id=c.route_id, area_id=area_ids[area_name] if area_name else None,
            complainant_type=c.complainant_type, bus_verification=c.bus_verification, synthetic_batch_id=batch.id,
            created_at=c.created, updated_at=c.path[-1][1],
            client_request_id=key(c.n), assigned_l2_user_id=l2 if status in (
                ComplaintStatus.FORWARDED, ComplaintStatus.UNDER_REVIEW) else None,
        )
        if status != ComplaintStatus.DRAFT:
            row.registered_at = first_non_draft
        if "incomplete" in when and status == ComplaintStatus.INCOMPLETE:
            row.paused_since = when["incomplete"]
        elif "incomplete" in when and "forwarded" in when:
            row.paused_total = when["forwarded"] - when["incomplete"]
        if "forwarded" in when:
            row.forwarded_at = when["forwarded"]
        if "under_review" in when:
            row.review_started_at = when["under_review"]
        if status == ComplaintStatus.REJECTED:
            row.rejected_at = when["rejected"]
            row.rejection_type = RejectionType.DUPLICATE if c.rejection == "duplicate" else RejectionType.INVALID
            row.rejection_reason = ("Duplicate of an earlier complaint about the same incident (synthetic)."
                                    if c.rejection == "duplicate" else "Could not be supported by the records (synthetic).")
            if c.rejection == "duplicate":
                row.duplicate_of_complaint_id = ids[c.duplicate_of]
        if status not in (ComplaintStatus.DRAFT, ComplaintStatus.REJECTED) or (status == ComplaintStatus.REJECTED and "incomplete" in when):
            row.reference_number = f"TEMP-{batch.id}-{c.n}"
        db.add(row)
        pending.append((c, row, trip, bus))
        if len(pending) >= COMPLAINT_BATCH:
            _finish_batch(db, pending, ids, batch, officers, owner_ids, driver_ids, conductor_ids, trip_ids, world, network, permit_numbers)
            finish()
    if pending:
        _finish_batch(db, pending, ids, batch, officers, owner_ids, driver_ids, conductor_ids, trip_ids, world, network, permit_numbers)
        finish()
    log(f"  complaints: {written} written")


def _finish_batch(db, pending, ids, batch, officers, owner_ids, driver_ids, conductor_ids, trip_ids, world, network, permit_numbers) -> None:
    db.flush()
    names = {}
    for c, row, trip, bus in pending:
        ids[c.n] = row.id
        if row.reference_number:
            row.reference_number = f"SPRPTA-{c.created.year}-{row.id:06d}"
        row.updated_at = c.path[-1][1]  # the simulated time, not the time this script ran
        flag_modified(row, "updated_at")  # include it in the UPDATE, or the column's onupdate would stamp now()
    for c, row, trip, bus in pending:
        if trip is not None and bus is not None:
            trip_id = trip_ids.get((trip.bus_id, trip.day, _t(trip.dep)))
            if trip_id is not None and row.bus_verification in ("verified", "corrected", "trip_cancelled"):
                route = network.routes[trip.route_id]
                owner = world.owners[trip.owner] if trip.owner is not None else None
                db.add(ComplaintDutySnapshot(
                    complaint_id=row.id, trip_id=trip_id, service_date=trip.day, bus_number=bus.number,
                    permit_number=permit_numbers[bus.permit_id], route_name=route.name, origin=trip.origin, destination=trip.destination,
                    departure_time=_t(trip.dep), owner_person_id=owner_ids.get(trip.owner), owner_name=owner,
                    driver_person_id=driver_ids.get(trip.driver), driver_name=world.drivers[trip.driver].name if trip.driver is not None else None,
                    conductor_person_id=conductor_ids.get(trip.conductor),
                    conductor_name=world.conductors[trip.conductor].name if trip.conductor is not None else None,
                    verification_status="Verified"))
        seq = 0
        previous = None
        db.add(SyntheticComplaintEvent(complaint_id=row.id, seq=seq, event="created", to_status="draft",
                                       occurred_at=c.created, actor_user_id=officers[c.officer],
                                       details={"scenario": c.scenario}, synthetic_batch_id=batch.id))
        previous = "draft"
        for status, moment in c.path[1:]:
            seq += 1
            db.add(SyntheticComplaintEvent(complaint_id=row.id, seq=seq, event="status_change", from_status=previous,
                                           to_status=status, occurred_at=moment, actor_user_id=officers[c.officer],
                                           synthetic_batch_id=batch.id))
            previous = status
        if c.verification is not None:
            seq += 1
            db.add(SyntheticComplaintEvent(
                complaint_id=row.id, seq=seq, event="bus_verification", occurred_at=c.created + timedelta(minutes=5),
                actor_user_id=officers[c.officer], synthetic_batch_id=batch.id,
                details={**c.verification, "outcome": c.bus_verification, "reported_bus": c.reported_bus,
                         "reported_date": c.reported_day.isoformat()}))
        if c.duplicate_of is not None and c.duplicate_link is not None:
            db.add(DuplicateCheck(complaint_id=row.id, candidate_complaint_id=ids[c.duplicate_of],
                                  link_type=DuplicateLinkType(c.duplicate_link), decided_by_user_id=officers[c.officer],
                                  decided_at=c.created + timedelta(minutes=3)))


def cleanup(db: Session, batch_name: str, log=print) -> dict:
    """Delete exactly what a batch created, nothing else."""
    check_environment()
    batch = db.scalar(select(SyntheticBatch).where(SyntheticBatch.name == batch_name))
    if batch is None:
        log("  no such batch")
        return {}
    bid = batch.id
    complaint_ids = select(Complaint.id).where(Complaint.synthetic_batch_id == bid)
    trip_ids = select(DailyTrip.id).where(DailyTrip.synthetic_batch_id == bid)
    counts = {}
    steps = [
        ("events", delete(SyntheticComplaintEvent).where(SyntheticComplaintEvent.synthetic_batch_id == bid)),
        ("snapshots", delete(ComplaintDutySnapshot).where(ComplaintDutySnapshot.complaint_id.in_(complaint_ids))),
        ("duplicate checks", delete(DuplicateCheck).where(DuplicateCheck.complaint_id.in_(complaint_ids))),
        ("complaints", delete(Complaint).where(Complaint.synthetic_batch_id == bid)),
        ("trip duties", delete(TripDuty).where(TripDuty.trip_id.in_(trip_ids))),
        ("trips", delete(DailyTrip).where(DailyTrip.synthetic_batch_id == bid)),
        ("ownership", delete(OwnerAssignment).where(OwnerAssignment.synthetic_batch_id == bid)),
        ("route authorizations", delete(RouteAuthorization).where(RouteAuthorization.synthetic_batch_id == bid)),
        ("non-operating periods", delete(BusNonOperation).where(BusNonOperation.synthetic_batch_id == bid)),
        ("people", delete(Person).where(Person.synthetic_batch_id == bid)),
    ]
    for label, statement in steps:
        counts[label] = db.execute(statement).rowcount
        log(f"  removed {counts[label]} {label}")
    db.delete(batch)
    db.commit()
    return counts
