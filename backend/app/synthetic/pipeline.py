"""Reading the real master data into a simulation network, planning a run, and the report of what it would create."""

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import PlaceKind, VehicleType
from app.models import Area, ComplaintCategory, ComplaintMedium, Permit, RouteStand, Severity, Vehicle
from app.synthetic import complaints as complaint_sim
from app.synthetic import simulate as sim
from app.synthetic.config import Config

BYTES_PER_TRIP = 850  # measured on the development database: a trip, its duty row and their indexes
TRIPS_PER_SECOND = 1300  # measured on this machine with batched inserts


@dataclass
class Plan:
    cfg: Config
    network: sim.Network
    route_ids: set[int]
    world: sim.World
    complaints: list[complaint_sim.SynComplaint]
    categories: list[str]
    n_mediums: int
    master_routes: int  # routes in the master data that have at least one bus
    permits_with_route: int

    def report(self) -> dict:
        trips = self.world.trips
        status = Counter(t.status for t in trips)
        tiers = Counter(self.network.routes[r].tier for r in self.route_ids)
        buses = [b for b in self.network.buses if b.route_id in self.route_ids]
        by_route = Counter(t.route_id for t in trips)
        coverage = []
        for rid in sorted(self.network.routes):
            route = self.network.routes[rid]
            coverage.append({
                "route_id": rid, "route": route.name, "office": route.area, "origin": route.origin,
                "destination": route.destination, "buses": route.bus_count, "profile": route.tier,
                "leg_minutes_assumed": route.leg_minutes, "in_this_scale": rid in self.route_ids,
                "simulated_trips": by_route.get(rid, 0),
            })
        n_trips = len(trips)
        return {
            "batch": self.cfg.batch_name, "scale": self.cfg.scale, "window": [d.isoformat() for d in self.cfg.window()],
            "routes_in_master_data_with_buses": self.master_routes, "routes_in_this_scale": len(self.route_ids),
            "routes_by_profile": dict(tiers), "buses_simulated": len(buses), "permits_with_route": self.permits_with_route,
            "owners": len(self.world.owners), "drivers": len(self.world.drivers), "conductors": len(self.world.conductors),
            "trips": n_trips, "trips_by_status": dict(status),
            "operating_bus_days": len({(t.bus_id, t.day) for t in trips if t.status != "cancelled"}),
            "inactive_bus_days": sum((e - s).days + 1 for _b, s, e, _r in self.world.non_ops),
            "non_operating_periods": dict(Counter(r for *_x, r in self.world.non_ops)),
            "route_authorizations": len(self.world.auths),
            "complaints": len(self.complaints),
            "complaints_by_scenario": dict(Counter(c.scenario.split("_")[0] if c.scenario.startswith(("dup", "corrected", "unmatched", "inactive")) else c.scenario for c in self.complaints)),
            "complaints_by_target": dict(Counter(c.target for c in self.complaints)),
            "complaints_by_status": dict(Counter(c.status for c in self.complaints)),
            "estimated_database_mb": round((n_trips * BYTES_PER_TRIP + len(self.complaints) * 2500) / 1_048_576, 1),
            "estimated_minutes": round(n_trips / TRIPS_PER_SECOND / 60 + len(self.complaints) / 400 / 60, 1),
            "route_coverage": coverage,
        }


def load_network(db: Session, cfg: Config) -> tuple[sim.Network, int, int]:
    """Buses and routes from the master data: a bus belongs to the route recorded on its (first) permit."""
    area_names = {a.id: a.name for a in db.scalars(select(Area))}
    first = (
        select(Permit.vehicle_id, func.min(Permit.id).label("permit_id"))
        .where(Permit.route_stand_id.is_not(None)).group_by(Permit.vehicle_id).subquery()
    )
    rows = db.execute(
        select(Vehicle.id, Vehicle.vehicle_number, Vehicle.registered_area_id, first.c.permit_id, Permit.route_stand_id)
        .join(first, first.c.vehicle_id == Vehicle.id).join(Permit, Permit.id == first.c.permit_id)
        .where(Vehicle.vehicle_type == VehicleType.BUS, Vehicle.is_active).order_by(Vehicle.id)
    ).all()
    routes = {
        r.id: (r.name, area_names.get(r.area_id, "Unknown"))
        for r in db.scalars(select(RouteStand).where(RouteStand.kind == PlaceKind.ROUTE))
    }
    buses = [(v, n, area_names.get(a, "Unknown"), p, r) for v, n, a, p, r in rows if r in routes]
    permits_with_route = db.scalar(select(func.count()).select_from(Permit).where(Permit.route_stand_id.is_not(None))) or 0
    return sim.from_rows(buses, routes, cfg), permits_with_route, len({b[4] for b in buses})


def build_plan(db: Session, cfg: Config, n_officers: int = 4) -> Plan:
    network, permits_with_route, master_routes = load_network(db, cfg)
    if not network.buses:
        raise SystemExit(
            "No bus has a permit with a route. Run the master-data import again so permits record their route:\n"
            "  python -m app.scripts.import_master_data <path to Permit_Conductor_Driver_Separate.xlsx>"
        )
    route_ids = sim.select_routes(network, cfg)
    world = sim.simulate(network, route_ids, cfg)
    categories = [c.name for c in db.scalars(select(ComplaintCategory).where(ComplaintCategory.is_active).order_by(ComplaintCategory.id))]
    n_mediums = len(list(db.scalars(select(ComplaintMedium.id).where(ComplaintMedium.is_system.is_(False)))))
    if not categories or n_mediums == 0:
        raise SystemExit("The complaint categories or mediums are empty. Run `python -m app.scripts.seed` first.")
    complaints = complaint_sim.generate(
        network, world, cfg, categories, n_mediums, n_officers,
        float(cfg.section("general")["demo_officer_share"]), 0,
    )
    return Plan(cfg, network, route_ids, world, complaints, categories, n_mediums, master_routes, permits_with_route)


def write_report(report: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, default=str)


def summary_lines(report: dict) -> list[str]:
    keys = ["batch", "scale", "window", "routes_in_master_data_with_buses", "routes_in_this_scale", "routes_by_profile",
            "buses_simulated", "owners", "drivers", "conductors", "trips", "trips_by_status", "operating_bus_days",
            "inactive_bus_days", "non_operating_periods", "route_authorizations", "complaints", "complaints_by_target",
            "complaints_by_status", "estimated_database_mb", "estimated_minutes"]
    return [f"  {k}: {report[k]}" for k in keys]


def today() -> date:
    return date.today()
