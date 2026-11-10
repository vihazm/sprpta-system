import type { AreaStatus } from "./types";
import { Card, CardHeading, StatusDot, muted } from "./ui";

export function AreaCoverage({ areas, className = "" }: { areas: AreaStatus[]; className?: string }) {
  return (
    <Card className={`gap-3 ${className}`}>
      <CardHeading title="Area coverage" subtitle="Level 2 officer per area" />
      <ul className="flex list-none flex-col gap-2 p-0">
        {areas.map((area) => (
          <li
            key={area.name}
            className={`flex items-center gap-[0.6rem] rounded-[1.1rem] px-[0.9rem] py-3 ${
              area.hasOfficer ? "bg-stone-50" : "bg-red-50"
            }`}
          >
            <StatusDot tone={area.hasOfficer ? "ok" : "crit"} />
            <div className="min-w-0 flex-1">
              <p className="text-[0.85rem] font-extrabold">{area.name}</p>
              <p className={muted}>{area.hasOfficer ? "Officer assigned" : "No active officer"}</p>
            </div>
            <span className="font-display text-[1.05rem] tabular-nums">{area.vehicles}</span>
          </li>
        ))}
      </ul>
      <p className={muted}>The number on the right is registered vehicles.</p>
    </Card>
  );
}
