"""Synthetic complaints tied to the simulated operations: valid ones, duplicates, wrong bus numbers, buses that did
not operate, and ones that cannot be verified. Pure Python; the writer stores the result.

A complaint matching a simulated trip does not make its allegation true: the simulation only says the bus ran, who was
on duty and when. Fictional names and placeholder contacts only.
"""

import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

from app.synthetic.config import Config
from app.synthetic.simulate import Network, World, clock

LOCAL = timezone(timedelta(hours=5, minutes=30))  # Sri Lanka time

KEYWORDS = {
    "driver": ["reckless", "speed", "driv", "behav", "staff"],
    "conductor": ["ticket", "overcharg", "fare", "behav", "staff", "misconduct"],
    "bus_service": ["timetable", "route", "delay", "condition", "service"],
    "owner": ["condition", "maint", "vehicle", "service"],
    "other": [],
}
TEXTS = {
    "reckless": ["The bus was overtaking on a bend and nearly hit a motorcycle near {place}. Passengers were frightened.",
                 "The driver was racing another bus on the {route} route and braking hard at every stop."],
    "overcharg": ["I was charged more than the printed fare between {origin} and {destination} and was not given change.",
                  "The conductor asked for a higher fare than the other passengers paid for the same journey."],
    "ticket": ["No ticket was issued for the fare I paid from {origin}. The conductor said the machine was not working.",
               "I asked for a ticket three times and was ignored."],
    "behav": ["The staff member shouted at a passenger who asked to be let off at {place} and refused to stop.",
              "The crew were rude to an elderly passenger who could not climb in quickly."],
    "timetable": ["The bus left {origin} well before its usual time and passengers were left at the stand.",
                  "The {route} bus did not complete the journey and everyone was asked to get off at {place}."],
    "condition": ["The bus had broken seats, a leaking roof and the door would not close properly.",
                  "The vehicle was in poor condition, very dirty and overcrowded beyond its seats."],
    "default": ["The service on this bus was unsatisfactory on the date given. Details are in the complaint."],
}
SUBJECTS = {"reckless": "Reckless driving", "overcharg": "Overcharging", "ticket": "Ticket not issued",
            "behav": "Misconduct by crew", "timetable": "Service delay or early departure",
            "condition": "Condition of the vehicle", "default": "Complaint about the service"}
PLACES = ["the Kamburugamuwa junction", "the town clock", "the hospital stop", "the Fort stand", "the school junction"]
SEVERITY_WEIGHTS = [5, 20, 40, 35]  # in the order of the severities list: highest first
LOCATIONS = ["At the bus stand", "On the road near the junction", "Inside the bus", "At a bus halt"]


@dataclass
class SynComplaint:
    n: int
    scenario: str
    kind: str  # valid, wrong_number, non_operating, unverified, duplicate
    bus_id: int | None  # the bus the record is finally linked to (None while unverified)
    reported_bus: str | None  # exactly as the complainant gave it
    reported_day: date
    day: date  # complaint_date as saved (may be corrected)
    trip_index: int | None
    route_id: int | None
    target: str
    accused_kind: str | None  # driver, conductor, owner
    accused_index: int | None
    accused_text: str | None
    category: int
    severity: int
    medium: int
    complainant_type: str
    officer: int
    created: datetime
    path: list[tuple[str, datetime]]  # statuses in order, each with when it happened
    bus_verification: str | None
    subject: str
    description: str
    incident_time: int | None
    location: str | None
    name: str | None
    phone: str | None
    email: str | None
    rejection: str | None = None
    duplicate_of: int | None = None  # n of the earlier complaint
    duplicate_link: str | None = None  # duplicate_of, related or not_duplicate (the check's link type)
    verification: dict | None = None
    area: str | None = None

    @property
    def status(self) -> str:
        return self.path[-1][0]


def _pick(rng: random.Random, weights: dict[str, float]) -> str:
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def _category(rng: random.Random, target: str, names: list[str]) -> int:
    wanted = KEYWORDS[target]
    options = [i for i, n in enumerate(names) if any(k in n.lower() for k in wanted)] or list(range(len(names)))
    return rng.choice(options)


def _text(rng: random.Random, category_name: str, route, place: str) -> tuple[str, str]:
    key = next((k for k in TEXTS if k != "default" and k in category_name.lower()), None)
    if key is None:
        key = rng.choice(["reckless", "overcharg", "ticket", "behav", "timetable", "condition"])
    body = rng.choice(TEXTS[key]).format(origin=route.origin.title(), destination=route.destination.title(), place=place,
                                         route=route.name.split(" ")[0])
    return SUBJECTS[key], body


def _mutate(rng: random.Random, number: str, others: list[str]) -> tuple[str, str]:
    """A wrong version of a bus number and how it went wrong."""
    mode = rng.choice(["typo", "missing_char", "similar", "wrong_bus", "not_in_master"])
    digits = [i for i, c in enumerate(number) if c.isdigit()]
    if mode == "typo" and digits:
        i = rng.choice(digits)
        return number[:i] + str((int(number[i]) + rng.randint(1, 8)) % 10) + number[i + 1:], mode
    if mode == "missing_char" and len(number) > 3:
        i = rng.randrange(len(number))
        return number[:i] + number[i + 1:], mode
    if mode == "similar":
        swaps = {"0": "O", "O": "0", "1": "I", "I": "1", "8": "B", "B": "8", "5": "S", "S": "5"}
        spots = [i for i, c in enumerate(number) if c in swaps]
        if spots:
            i = rng.choice(spots)
            return number[:i] + swaps[number[i]] + number[i + 1:], mode
    if mode == "wrong_bus" and others:
        return rng.choice(others), mode
    return f"{rng.choice(['XX', 'SP'])} ZZ-{rng.randint(1000, 9999)}", "not_in_master"


def generate(network: Network, world: World, cfg: Config, categories: list[str], n_mediums: int, n_officers: int,
             demo_share: float, demo_index: int = 0) -> list[SynComplaint]:
    rules = cfg.section("complaints")
    rng = random.Random(f"{cfg.seed}:complaints:{cfg.scale}")
    buses = {b.id: b for b in network.buses}
    numbers = {b.id: b.number for b in network.buses}
    completed = [i for i, t in enumerate(world.trips) if t.status == "completed" and t.driver is not None]
    if not completed:
        return []
    route_factor = {r.id: cfg.section("profiles")[r.tier]["complaint_weight"] * rng.lognormvariate(0, 0.35)
                    for r in network.routes.values()}
    ceiling = max(route_factor.values())

    def sample_trip() -> int:
        while True:
            i = rng.choice(completed)
            if rng.random() < route_factor[world.trips[i].route_id] / ceiling:
                return i

    total = max(int(cfg.scale_settings["min_complaints"]), round(len(completed) * rules["per_10k_trips"] / 10_000))
    n_nonop = round(total * rules["non_operating_rate"])
    n_wrong = round(total * rules["wrong_bus_number_rate"])
    n_unverified = round(total * rules["verification_failure_rate"])
    n_dup = round(total * rules["duplicate_rate"])
    n_valid = max(1, total - n_nonop - n_wrong - n_unverified - n_dup)

    out: list[SynComplaint] = []
    first_day, last_day = cfg.window()

    def officer() -> int:
        if rng.random() < demo_share or n_officers == 1:
            return demo_index
        return rng.choice([i for i in range(n_officers) if i != demo_index])

    def created_after(day: date, hours: float = 0) -> datetime:
        base = datetime.combine(day + timedelta(days=rng.randint(0, 3)), time(rng.randint(8, 16), rng.randint(0, 59)), LOCAL)
        return min(base + timedelta(hours=hours), datetime.combine(last_day + timedelta(days=2), time(17), LOCAL))

    def path(kind: str, verified: bool, start: datetime) -> list[tuple[str, datetime]]:
        """A status path that follows the allowed transitions. Unverified bus: nothing past incomplete or rejected."""
        steps = [("draft", start)]
        clock_at = start

        def step(status: str, minutes: tuple[int, int] = (20, 2000)) -> None:
            nonlocal clock_at
            clock_at = clock_at + timedelta(minutes=rng.randint(*minutes))
            steps.append((status, clock_at))

        table = {"valid": [("draft", 12), ("incomplete", 12), ("forwarded", 62), ("under_review", 10), ("rejected", 4)]}
        options = table["valid"] if verified else [("draft", 15), ("incomplete", 62), ("rejected", 23)]
        final = rng.choices([s for s, _w in options], weights=[w for _s, w in options])[0]
        if final == "draft":
            return steps
        if final == "rejected":
            if rng.random() < 0.4:
                step("incomplete")
            step("rejected")
        elif final == "incomplete":
            step("incomplete")
        else:
            if rng.random() < 0.25:
                step("incomplete")
            step("forwarded")
            if final == "under_review":
                step("under_review", (600, 4000))
        return steps

    def build(scenario: str, kind: str, trip_index: int | None, *, bus_id: int | None, reported: str | None,
              day: date, reported_day: date, target: str | None = None, link_trip: bool = True) -> SynComplaint:
        trip = world.trips[trip_index] if trip_index is not None else None
        route_id = trip.route_id if trip else (buses[bus_id].route_id if bus_id in buses else None)
        route = network.routes.get(route_id) if route_id else None
        target = target or _pick(rng, rules["target_weights"])
        accused_kind = accused_index = accused_text = None
        if target in ("driver", "conductor") and trip is not None:
            if rng.random() < 0.8:
                accused_kind = target
                accused_index = trip.driver if target == "driver" else trip.conductor
            else:
                accused_text = f"the {target} (name not known)"
        elif target == "owner" and trip is not None and trip.owner is not None and rng.random() < 0.7:
            accused_kind, accused_index = "owner", trip.owner
        elif target == "other":
            accused_text = "a person at the stand"
        category = _category(rng, target, categories)
        subject, body = _text(rng, categories[category], route or next(iter(network.routes.values())), rng.choice(PLACES))
        anonymous = rng.random() < 0.1
        n = len(out) + 1
        verified = kind in ("valid", "duplicate") or scenario.startswith("corrected") or scenario == "cancelled_service"
        start = created_after(reported_day)
        c = SynComplaint(
            n=n, scenario=scenario, kind=kind, bus_id=bus_id, reported_bus=reported, reported_day=reported_day, day=day,
            trip_index=trip_index if link_trip else None, route_id=route_id, target=target, accused_kind=accused_kind,
            accused_index=accused_index, accused_text=accused_text, category=category,
            severity=rng.choices(range(4), weights=SEVERITY_WEIGHTS)[0], medium=rng.randrange(n_mediums),
            complainant_type=_pick(rng, rules["complainant_weights"]), officer=officer(), created=start,
            path=path(kind, verified, start), bus_verification=None, subject=subject, description=body,
            incident_time=(trip.a_dep or trip.dep) + rng.randint(0, max(1, (trip.a_arr or trip.arr) - (trip.a_dep or trip.dep)))
            if trip else None,
            location=rng.choice(LOCATIONS),
            name=None if anonymous else f"Test Passenger {n:05d}",
            phone=None if anonymous else f"0700{n:06d}"[:10], email=None if anonymous else f"test{n:05d}@example.invalid",
        )
        out.append(c)
        return c

    # ---- valid complaints about a trip that really ran
    for _ in range(n_valid):
        i = sample_trip()
        t = world.trips[i]
        c = build("valid", "valid", i, bus_id=t.bus_id, reported=numbers[t.bus_id], day=t.day, reported_day=t.day)
        c.bus_verification = "verified"

    # ---- a real bus and date that no trip record supports
    by_bus_day = defaultdict(list)
    for i, t in enumerate(world.trips):
        by_bus_day[(t.bus_id, t.day)].append(i)
    for _ in range(n_unverified):
        i = sample_trip()
        t = world.trips[i]
        c = build("unverified_record", "unverified", None, bus_id=t.bus_id, reported=numbers[t.bus_id], day=t.day,
                  reported_day=t.day)
        c.bus_verification = "unverified"
        c.verification = {"finding": "The bus and date exist but no selectable verified trip record supports the complaint."}

    # ---- wrong bus numbers
    for _ in range(n_wrong):
        i = sample_trip()
        t = world.trips[i]
        wrong, how = _mutate(rng, numbers[t.bus_id], [numbers[b] for b in rng.sample(list(numbers), min(5, len(numbers)))
                                                      if b != t.bus_id])
        correctable = how != "not_in_master" and rng.random() < 0.6
        if correctable:
            c = build(f"corrected_{how}", "wrong_number", i, bus_id=t.bus_id, reported=wrong, day=t.day, reported_day=t.day)
            c.bus_verification = "corrected"
            c.verification = {"finding": "Bus number corrected after checking the daily records.", "reported": wrong,
                              "corrected_to": numbers[t.bus_id], "mistake": how}
        else:
            c = build(f"unmatched_{how}", "wrong_number", None, bus_id=None, reported=wrong, day=t.day, reported_day=t.day)
            c.bus_verification = "not_found"
            c.verification = {"finding": "No bus on record matches the reported number.", "reported": wrong, "mistake": how}

    # ---- buses that did not operate on the reported date
    nonop_days = [(bus, start, end, reason) for bus, start, end, reason in world.non_ops if reason != "rest_day"]
    cancelled = [i for i, t in enumerate(world.trips) if t.status == "cancelled"]
    operated_days = defaultdict(set)
    for t in world.trips:
        if t.status != "cancelled":
            operated_days[t.bus_id].add(t.day)
    made_nonop = len(out)
    attempts = 0
    # A draw that cannot be placed (a date outside the window, a day the bus did run) is skipped and drawn again, so the
    # planned number is really made.
    while len(out) - made_nonop < n_nonop and attempts < n_nonop * 50:
        attempts += 1
        roll = rng.random()
        if cancelled and roll < 0.30:
            i = rng.choice(cancelled)
            t = world.trips[i]
            if t.day in operated_days[t.bus_id]:
                continue_case = False
            else:
                continue_case = True
            outcome = rng.random()
            if outcome < 0.30:  # the complaint is about the cancelled service itself, and it is forwarded
                c = build("cancelled_service", "non_operating", i, bus_id=t.bus_id, reported=numbers[t.bus_id], day=t.day,
                          reported_day=t.day, target="bus_service")
                c.bus_verification = "trip_cancelled"
                c.verification = {"finding": "The trip was cancelled; the complaint concerns the cancellation.", "trip_cancelled": True}
                continue
            c = build("cancelled_trip_reported_as_run", "non_operating", None, bus_id=t.bus_id, reported=numbers[t.bus_id],
                      day=t.day, reported_day=t.day)
            c.bus_verification = "trip_cancelled"
            c.verification = {"finding": "The reported trip was cancelled.", "same_day_other_trips": not continue_case}
            continue
        if nonop_days and roll < 0.70:
            bus, start, end, reason = rng.choice(nonop_days)
            day = start + timedelta(days=rng.randrange((end - start).days + 1))
            if day < first_day or day > last_day or bus not in numbers:
                continue
            c = build(f"inactive_{reason}", "non_operating", None, bus_id=bus, reported=numbers[bus], day=day, reported_day=day)
            c.bus_verification = "not_operated"
            c.verification = {"finding": f"The bus did not operate on that date ({reason.replace('_', ' ')}).", "reason": reason}
            continue
        i = sample_trip()  # the bus ran, but on a different day than the complainant said
        t = world.trips[i]
        shift = rng.choice([-3, -2, -1, 1, 2, 3])
        wrong_day = t.day + timedelta(days=shift)
        if wrong_day in operated_days[t.bus_id] or not (first_day <= wrong_day <= last_day):
            continue
        if rng.random() < 0.45:
            c = build("corrected_date", "non_operating", i, bus_id=t.bus_id, reported=numbers[t.bus_id], day=t.day,
                      reported_day=wrong_day)
            c.bus_verification = "corrected"
            c.verification = {"finding": "The bus did not operate on the reported date; it operated on another date.",
                              "reported_date": wrong_day.isoformat(), "corrected_date": t.day.isoformat()}
        else:
            c = build("operated_another_date", "non_operating", None, bus_id=t.bus_id, reported=numbers[t.bus_id],
                      day=wrong_day, reported_day=wrong_day)
            c.bus_verification = "not_operated"
            c.verification = {"finding": "The bus did not operate on the reported date.", "operated_on": t.day.isoformat()}

    # ---- duplicates: more complaints about incidents already reported, and some that only look alike
    bases = [c for c in out if c.kind == "valid" and c.status != "draft"]
    kinds = ["exact", "near_different_wording", "same_person_twice", "cross_medium", "different_incident_same_bus_day",
             "related_not_duplicate"]
    made = 0
    while made < n_dup and bases:
        base = rng.choice(bases)
        scenario = rng.choice(kinds)
        trip = world.trips[base.trip_index]
        extra = build("dup_" + scenario, "duplicate", base.trip_index, bus_id=base.bus_id, reported=base.reported_bus,
                      day=base.day, reported_day=base.reported_day, target=base.target)
        extra.bus_verification = "verified"
        extra.duplicate_of = base.n
        if scenario == "exact":
            extra.subject, extra.description, extra.category = base.subject, base.description, base.category
        elif scenario == "same_person_twice":
            extra.subject, extra.description, extra.category = base.subject, base.description, base.category
            extra.name, extra.phone, extra.email = base.name, base.phone, base.email
        elif scenario == "cross_medium":
            extra.subject, extra.description, extra.category = base.subject, base.description, base.category
            extra.medium = (base.medium + 1) % n_mediums
        elif scenario == "near_different_wording":
            extra.category = base.category
            extra.accused_kind, extra.accused_index = base.accused_kind, base.accused_index
        elif scenario == "different_incident_same_bus_day":
            extra.duplicate_link = "not_duplicate"
            extra.incident_time = min(23 * 60, (base.incident_time or trip.dep) + rng.randint(90, 240))
            extra.duplicate_of = base.n  # shown as a candidate and judged not a duplicate
        else:  # related_not_duplicate
            extra.duplicate_link = "related"
        if scenario in ("exact", "near_different_wording", "same_person_twice", "cross_medium"):
            extra.duplicate_link = "duplicate_of"
            if rng.random() < 0.55:  # the officer rejects it as a duplicate of the earlier case
                extra.rejection = "duplicate"
                start = extra.path[0][1]
                extra.path = [("draft", start), ("rejected", start + timedelta(minutes=rng.randint(10, 600)))]
        if extra.created < base.created:  # the duplicate arrives after the case it repeats
            gap = base.created - extra.created + timedelta(hours=rng.randint(1, 40))
            extra.created += gap
            extra.path = [(s, w + gap) for s, w in extra.path]
        made += 1

    # Nothing happens after the end of the period: cap every timestamp (the order is kept, ties allowed).
    cap = datetime.combine(last_day, time(21, 0), LOCAL)
    for c in out:
        c.created = min(c.created, cap)
        c.path = [(s, min(w, cap)) for s, w in c.path]
    return out


def describe(c: SynComplaint) -> str:
    return f"{c.n:05d} {c.scenario} {c.status} {clock(c.incident_time) if c.incident_time else '--:--'}"
