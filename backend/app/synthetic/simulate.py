"""The simulation of bus operations. Pure Python: it reads a network (routes and buses) and returns what happened.

Every bus is simulated with its own random generator seeded from the batch seed and the bus id, so the same
configuration always produces the same data, and adding or removing other buses does not change a bus's year.
Times are minutes since midnight, Sri Lanka local time. None of this is real operating history.
"""

import math
import random
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.synthetic.config import Config

FIRST = ["Nuwan", "Kasun", "Chaminda", "Saman", "Ruwan", "Pradeep", "Lasantha", "Dinesh", "Asanka", "Sampath",
         "Thilina", "Mahesh", "Nimal", "Sunil", "Janaka", "Gayan", "Chathura", "Buddhika", "Ajith", "Rohan",
         "Kamal", "Upul", "Sarath", "Damith", "Isuru", "Harsha", "Indika", "Prasanna", "Tharanga", "Wasantha"]
LAST = ["Perera", "Silva", "Fernando", "Jayasinghe", "Wickramasinghe", "Rathnayake", "Gunawardena", "Dissanayake",
        "Bandara", "Weerasinghe", "Herath", "Karunaratne", "Samaraweera", "Amarasinghe", "Liyanage", "Abeysekara",
        "Pathirana", "Ranasinghe", "Senanayake", "Kodithuwakku", "Mendis", "Jayawardena", "Gamage", "Hettiarachchi"]
TIERS = ("high", "medium", "low_mid", "low")
ROUTE_CHANGE_REASONS = ["Temporary replacement service while another bus was out of service",
                        "Schedule adjustment approved for the period", "Seasonal demand cover"]


def person_name(kind: str, index: int) -> str:
    """A made-up name. The suffix keeps it from ever being mistaken for a real person."""
    rng = random.Random(f"{kind}:{index}")
    return f"{rng.choice(FIRST)} {rng.choice(LAST)} (Test)"


def clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def minutes_of(text: str) -> int:
    hour, minute = text.split(":")
    return int(hour) * 60 + int(minute)


def route_ends(name: str) -> tuple[str, str]:
    """Origin and destination from a route name such as '24/1 Avithtawa - Elpitiya'."""
    clean = re.sub(r"\s*\(.*?\)\s*$", "", name).strip()
    first = clean.split(" ")[0]
    if any(ch.isdigit() for ch in first) and " " in clean:
        clean = clean.split(" ", 1)[1]
    parts = [x.strip() for x in clean.split(" - ")]
    origin, destination = (parts[0], parts[-1]) if len(parts) > 1 else (clean, clean)
    return origin[:100] or "Depot", destination[:100] or "Depot"


@dataclass(frozen=True)
class Route:
    id: int
    name: str
    origin: str
    destination: str
    area: str
    tier: str
    leg_minutes: int  # one-way duration: an assumption, not a published timetable
    bus_count: int


@dataclass(frozen=True)
class Bus:
    id: int
    number: str
    area: str
    permit_id: int
    route_id: int  # the route of its permit


@dataclass
class Network:
    routes: dict[int, Route]
    buses: list[Bus]


@dataclass(slots=True)
class Trip:
    bus_id: int
    day: date
    route_id: int
    direction: str  # outbound or return
    origin: str
    destination: str
    dep: int  # scheduled departure
    arr: int  # scheduled arrival
    a_dep: int | None
    a_arr: int | None
    status: str  # completed, cancelled or partial
    driver: int | None = None  # index into World.drivers
    conductor: int | None = None
    d_start: int | None = None  # the driver's duty on this block of trips
    d_end: int | None = None
    c_start: int | None = None
    c_end: int | None = None
    owner: int | None = None  # index into World.owners, for the trip date


@dataclass
class Staff:
    name: str
    area: str
    kind: str  # regular or relief


@dataclass
class World:
    owners: list[str] = field(default_factory=list)
    ownership: list[tuple[int, int, date, date | None]] = field(default_factory=list)  # bus, owner, from, to
    drivers: list[Staff] = field(default_factory=list)
    conductors: list[Staff] = field(default_factory=list)
    non_ops: list[tuple[int, date, date, str]] = field(default_factory=list)  # bus, from, to, reason
    auths: list[tuple[int, int, date, date | None, str]] = field(default_factory=list)  # bus, route, from, to, reason
    trips: list[Trip] = field(default_factory=list)
    bus_crew: dict[int, tuple[int, int]] = field(default_factory=dict)  # bus -> regular driver, conductor


# ---------------------------------------------------------------- the network


def tier_for(bus_count: int, cfg: Config) -> str:
    for tier in TIERS:
        if bus_count >= cfg.section("profiles")[tier]["min_buses"]:
            return tier
    return "low"


def from_rows(buses: list[tuple[int, str, str, int, int]], routes: dict[int, tuple[str, str]], cfg: Config) -> Network:
    """buses: (id, number, area, permit id, route id); routes: id -> (name, area). Routes with no bus are left out."""
    counts: dict[int, int] = {}
    for _id, _n, _a, _p, route_id in buses:
        counts[route_id] = counts.get(route_id, 0) + 1
    network_routes = {}
    for route_id, count in counts.items():
        name, area = routes[route_id]
        tier = tier_for(count, cfg)
        lo, hi = cfg.section("profiles")[tier]["leg_minutes"]
        origin, destination = route_ends(name)
        leg = random.Random(f"leg:{route_id}").randint(lo, hi)
        network_routes[route_id] = Route(route_id, name, origin, destination, area, tier, leg, count)
    return Network(network_routes, [Bus(*b) for b in buses])


def select_routes(network: Network, cfg: Config) -> set[int]:
    """The routes simulated at this scale, chosen the same way every time and covering every size profile."""
    settings = cfg.scale_settings
    ranked = sorted(network.routes.values(), key=lambda r: (-r.bus_count, r.id))
    if "route_fraction" in settings:
        keep = float(settings["route_fraction"])
        if keep >= 1.0:
            return {r.id for r in ranked}
        chosen = set()
        for tier in TIERS:  # the same share of each size, biggest first
            of_tier = [r for r in ranked if r.tier == tier]
            chosen |= {r.id for r in of_tier[: max(1, math.ceil(len(of_tier) * keep))]}
        return chosen
    per = int(settings["routes_per_tier_per_office"])
    chosen = set()
    for area in sorted({r.area for r in ranked}):
        for tier in TIERS[:3] + ("low",):
            of_tier = [r for r in ranked if r.area == area and r.tier == tier]
            if tier == "low_mid" and not of_tier:
                continue
            chosen |= {r.id for r in of_tier[:per]}
    return chosen


# ---------------------------------------------------------------- one bus's year


def _intervals(days: dict[date, str]) -> list[tuple[date, date, str]]:
    """Consecutive days with the same reason become one period."""
    out: list[tuple[date, date, str]] = []
    for day in sorted(days):
        if out and out[-1][2] == days[day] and out[-1][1] + timedelta(days=1) == day:
            out[-1] = (out[-1][0], day, days[day])
        else:
            out.append((day, day, days[day]))
    return out


def _non_operating_days(rng: random.Random, first: date, last: date, cfg: Config) -> dict[date, str]:
    rules = cfg.section("non_operation")
    span = (last - first).days + 1
    marked: dict[date, str] = {}

    def event(per_year: float, days: list[int], reason: str) -> None:
        count = int(per_year * span / 365 + rng.random())
        for _ in range(count):
            length = rng.randint(*days)
            start = first + timedelta(days=rng.randrange(span))
            period = [start + timedelta(days=n) for n in range(length)]
            if all(first <= d <= last and d not in marked for d in period):
                marked.update({d: reason for d in period})

    event(rules["maintenance_per_bus_year"], rules["maintenance_days"], "maintenance")
    event(rules["permit_suspension_per_bus_year"], rules["permit_suspension_days"], "permit_suspension")
    event(rules["breakdown_per_bus_year"], rules["breakdown_days"], "breakdown")
    for n in range(span):
        day = first + timedelta(days=n)
        chance = rules["sunday_rest_day_probability"] if day.weekday() == 6 else rules["rest_day_probability"]
        if day not in marked and rng.random() < chance:
            marked[day] = "rest_day"
    return marked


def _route_plan(rng: random.Random, bus: Bus, area_routes: list[int], first: date, last: date, cfg: Config):
    """Route changes for the period: [(route id, from, to or None, reason)]. The permit's own route is the default."""
    rules = cfg.section("route_changes")
    others = [r for r in area_routes if r != bus.route_id]
    plan: list[tuple[int, date, date | None, str]] = []
    if not others:
        return plan
    span = (last - first).days + 1
    roll = rng.random()
    if roll < rules["permanent_probability"] and span > 30:
        plan.append((rng.choice(others), first + timedelta(days=rng.randrange(span // 4, span - 10)), None, ROUTE_CHANGE_REASONS[1]))
    elif roll < rules["permanent_probability"] + rules["temporary_probability"]:
        length = rng.randint(*rules["temporary_days"])
        start = first + timedelta(days=rng.randrange(max(1, span - length)))
        plan.append((rng.choice(others), start, start + timedelta(days=length - 1), rng.choice([ROUTE_CHANGE_REASONS[0], ROUTE_CHANGE_REASONS[2]])))
    return plan


def _free(busy: dict, person: int, day: date, start: int, end: int) -> bool:
    return all(end <= s or start >= e for s, e in busy.get((person, day), ()))


def simulate(network: Network, route_ids: set[int], cfg: Config) -> World:
    """Simulate every bus on the chosen routes over the scale's window."""
    first, last = cfg.window()
    world = World()
    buses = sorted((b for b in network.buses if b.route_id in route_ids), key=lambda b: b.id)
    area_routes: dict[str, list[int]] = {}
    for route in network.routes.values():
        if route.id in route_ids:
            area_routes.setdefault(route.area, []).append(route.id)
    staff = cfg.section("staff")
    timetable = cfg.section("timetable")
    profiles = cfg.section("profiles")

    # People: a regular driver and conductor per bus, and a relief pool per office.
    for bus in buses:
        world.bus_crew[bus.id] = (len(world.drivers), len(world.conductors))
        world.drivers.append(Staff(person_name("driver", len(world.drivers)), bus.area, "regular"))
        world.conductors.append(Staff(person_name("conductor", len(world.conductors)), bus.area, "regular"))
    relief: dict[str, tuple[list[int], list[int]]] = {}
    for area in sorted({b.area for b in buses}):
        n = max(2, math.ceil(sum(1 for b in buses if b.area == area) * staff["relief_pool_share"]))
        ds, cs = [], []
        for _ in range(n):
            ds.append(len(world.drivers))
            world.drivers.append(Staff(person_name("driver", len(world.drivers)), area, "relief"))
            cs.append(len(world.conductors))
            world.conductors.append(Staff(person_name("conductor", len(world.conductors)), area, "relief"))
        relief[area] = (ds, cs)

    _ownership(world, buses, cfg)
    owner_of = _owner_lookup(world)
    rank_in_route: dict[int, dict[int, int]] = {}
    for bus in buses:
        rank_in_route.setdefault(bus.route_id, {})[bus.id] = len(rank_in_route.get(bus.route_id, {}))
    busy: dict[tuple[int, date], list[tuple[int, int]]] = {}  # (person key, day) -> duty intervals
    busy_d: dict = {}
    busy_c: dict = {}

    for bus in buses:
        rng = random.Random(f"{cfg.seed}:{bus.id}")
        marked = _non_operating_days(rng, first, last, cfg)
        plan = _route_plan(rng, bus, area_routes.get(bus.area, []), first, last, cfg)
        for route_id, start, end, reason in plan:
            world.auths.append((bus.id, route_id, start, end, reason))
        regular_d, regular_c = world.bus_crew[bus.id]
        relief_d, relief_c = relief[bus.area]
        n_days = (last - first).days + 1
        dense_days = cfg.scale_settings.get("dense_days")
        sample_before = last - timedelta(days=int(dense_days) - 1) if dense_days else None
        earlier_fraction = float(cfg.scale_settings.get("earlier_day_fraction", 1.0))
        for offset in range(n_days):
            day = first + timedelta(days=offset)
            if day in marked:
                continue
            if sample_before and day < sample_before and rng.random() >= earlier_fraction:
                continue  # an earlier day that this scale does not simulate: no record at all
            route_id = bus.route_id
            for r, start, end, _reason in plan:
                if start <= day and (end is None or day <= end):
                    route_id = r
            route = network.routes[route_id]
            prof = profiles[route.tier]
            legs = rng.choice(prof["legs"])
            service_start, service_end = minutes_of(prof["service_start"]), minutes_of(prof["service_end"])
            fraction = (rank_in_route[bus.route_id][bus.id] * 7 + bus.id % 13) % 10 / 10
            t = service_start + int(timetable["stagger_minutes"] * fraction) + rng.randint(-5, 10)
            free_at = 0
            rest_after = math.ceil(legs / 2) if legs >= 3 else None
            plan_legs: list[Trip] = []
            broke = False
            for leg in range(1, legs + 1):
                dep = max(t, free_at, service_start)
                if dep > service_end + 60 and plan_legs:
                    break
                duration = max(15, route.leg_minutes + rng.randint(-5, 5))
                arr = dep + duration
                if arr >= 23 * 60:
                    break
                outbound = leg % 2 == 1
                trip = Trip(bus.id, day, route.id, "outbound" if outbound else "return",
                            route.origin if outbound else route.destination, route.destination if outbound else route.origin,
                            dep, arr, None, None, "completed", owner=owner_of(bus.id, day))
                roll = rng.random()
                delay = rng.randint(*timetable["delay_minutes"]) if rng.random() < timetable["delay_probability"] else rng.randint(0, 4)
                if roll < timetable["cancel_trip_probability"]:
                    trip.status = "cancelled"
                    free_at = arr + rng.randint(*timetable["turnaround_minutes"])
                elif roll < timetable["cancel_trip_probability"] + timetable["partial_trip_probability"]:
                    trip.status, trip.a_dep = "partial", dep + delay
                    trip.a_arr = trip.a_dep + rng.randint(10, max(11, duration - 5))
                    plan_legs.append(trip)
                    broke = True
                    break
                else:
                    trip.a_dep = dep + delay
                    trip.a_arr = arr + delay + rng.randint(-3, 6)
                    free_at = max(arr, trip.a_arr) + rng.randint(*timetable["turnaround_minutes"])
                plan_legs.append(trip)
                t = free_at
                if rest_after == leg:
                    t = free_at + rng.randint(*timetable["rest_break_minutes"])
            if not plan_legs:
                continue

            running = [x for x in plan_legs if x.status != "cancelled"]
            if running:
                _crew(rng, world, bus, day, running, rest_after, plan_legs, regular_d, regular_c, relief_d, relief_c,
                      busy_d, busy_c, staff, marked)
                if day in marked:  # nobody could be found: the bus did not run
                    continue
            world.trips.extend(plan_legs)
            if broke:
                length = rng.randint(*cfg.section("non_operation")["breakdown_days"])
                for n in range(1, length + 1):
                    later = day + timedelta(days=n)
                    if later <= last and later not in marked:
                        marked[later] = "breakdown"

        for start, end, reason in _intervals(marked):
            world.non_ops.append((bus.id, start, end, reason))
    return world


def _crew(rng, world, bus, day, running, rest_after, plan_legs, reg_d, reg_c, relief_d, relief_c, busy_d, busy_c, staff, marked):
    """Give the running trips their driver and conductor: the regular ones, or relief when they are away or the shift changes."""
    first_dep, last_arr = running[0].dep - 10, (running[-1].a_arr or running[-1].arr) + 10
    split_at = None
    if rest_after is not None and len(running) >= 3 and rng.random() < staff["shift_change_probability"]:
        split_at = plan_legs[rest_after - 1].arr  # the second half starts after this time
    drivers_away = rng.random() < staff["replacement_day_probability"]
    conductors_away = rng.random() < staff["replacement_day_probability"]

    def pick(pool, busy, start, end):
        at = rng.randrange(len(pool))
        for person in pool[at:] + pool[:at]:
            if _free(busy, person, day, start, end):
                return person
        return None

    def block(trips, regular, away, pool, busy):
        if not trips:
            return None
        start, end = trips[0].dep - 10, (trips[-1].a_arr or trips[-1].arr) + 10
        person = regular
        if away or not _free(busy, regular, day, start, end):
            person = pick(pool, busy, start, end)
        return person, start, end

    halves = [running] if split_at is None else [[x for x in running if x.dep <= split_at], [x for x in running if x.dep > split_at]]
    for index, trips in enumerate(halves):
        if not trips:
            continue
        # With a shift change the first half keeps the regular crew; the second half is worked by relief staff.
        change = split_at is not None and index == 1
        who_d = block(trips, reg_d, drivers_away or (change and rng.random() < 0.6), relief_d, busy_d)
        who_c = block(trips, reg_c, conductors_away or (change and rng.random() < 0.6), relief_c, busy_c)
        if who_d is None or who_d[0] is None:
            marked[day] = "driver_unavailable"
            return
        if who_c is None or who_c[0] is None:
            marked[day] = "conductor_unavailable"
            return
        (d, ds, de), (c, cs, ce) = who_d, who_c
        busy_d.setdefault((d, day), []).append((ds, de))
        busy_c.setdefault((c, day), []).append((cs, ce))
        for trip in trips:
            trip.driver, trip.d_start, trip.d_end = d, ds, de
            trip.conductor, trip.c_start, trip.c_end = c, cs, ce


# ---------------------------------------------------------------- ownership


def _ownership(world: World, buses: list[Bus], cfg: Config) -> None:
    rules = cfg.section("ownership")
    rng = random.Random(f"{cfg.seed}:owners")
    sizes = [(1, 1, rules["single"]), (2, 2, rules["two"]), (3, 5, rules["three_to_five"]), (6, 12, rules["six_to_twelve"])]
    by_area: dict[str, list[Bus]] = {}
    for bus in buses:
        by_area.setdefault(bus.area, []).append(bus)
    first = cfg.start
    last = cfg.end
    for area in sorted(by_area):
        pool = by_area[area][:]
        rng.shuffle(pool)
        while pool:
            lo, hi, _share = rng.choices(sizes, weights=[s[2] for s in sizes])[0]
            size = rng.randint(lo, hi)
            group, pool = pool[:size], pool[size:]
            owner = len(world.owners)
            world.owners.append(person_name("owner", owner))
            for bus in group:
                world.ownership.append((bus.id, owner, first, None))
    # Some buses change owner once: the old period closes the day before the new one starts.
    changed = [i for i, row in enumerate(world.ownership) if rng.random() < rules["change_probability"]]
    for i in changed:
        bus_id, old, start, _end = world.ownership[i]
        when = first + timedelta(days=rng.randrange(30, max(31, (last - first).days - 10)))
        new = rng.randrange(len(world.owners))
        if new == old:
            new = len(world.owners)
            world.owners.append(person_name("owner", new))
        world.ownership[i] = (bus_id, old, start, when - timedelta(days=1))
        world.ownership.append((bus_id, new, when, None))


def _owner_lookup(world: World):
    by_bus: dict[int, list[tuple[int, date, date | None]]] = {}
    for bus_id, owner, start, end in world.ownership:
        by_bus.setdefault(bus_id, []).append((owner, start, end))

    def owner_on(bus_id: int, day: date) -> int | None:
        for owner, start, end in by_bus.get(bus_id, ()):
            if start <= day and (end is None or day <= end):
                return owner
        return None

    return owner_on
