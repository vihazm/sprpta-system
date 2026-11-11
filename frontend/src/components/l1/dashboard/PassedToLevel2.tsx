import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, bigNumber, muted } from "@/components/dashboard/ui";
import type { AreaTotal } from "./types";

// How many complaints went to each area officer. The area is the one the vehicle is registered in.
export function PassedToLevel2({ areas, className = "" }: { areas: AreaTotal[]; className?: string }) {
  const total = areas.reduce((sum, a) => sum + a.count, 0);
  const uncovered = areas.filter((a) => !a.hasOfficer).map((a) => a.name);

  return (
    <Card className={className}>
      <CardHeading title="Passed to Level 2" subtitle={`Per area officer · this month · ${total} total`} />
      <div className="grid gap-3 sm:grid-cols-3">
        {areas.map((area) => {
          const share = Math.round((area.count / total) * 100);
          return (
            <div key={area.name} className="rounded-[1.4rem] bg-[#f7f4f5] p-4">
              <p className={`${muted} font-bold`}>{area.name}</p>
              <p className={`${bigNumber} mt-1 text-[2.6rem]`}>{area.count}</p>
              <div className="mt-2.5 h-2 overflow-hidden rounded-full bg-[#ece4e7]">
                <div className="h-full rounded-full bg-crimson" style={{ width: `${share}%` }} />
              </div>
              <p className={`${muted} mt-1.5`}>{share}% of forwarded</p>
            </div>
          );
        })}
      </div>
      <Note tone="rose">
        Area rule: the officer is chosen from the area where the vehicle is registered.
        {uncovered.length > 0 &&
          ` ${uncovered.join(" and ")} has no active Level 2 officer, so complaints for it cannot be forwarded until one is assigned.`}
      </Note>
    </Card>
  );
}
