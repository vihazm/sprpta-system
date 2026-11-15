import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, bigNumber, muted } from "@/components/dashboard/ui";
import type { AreaTotal } from "./types";

// How many of this officer's complaints went to each area officer this month. The area is the one the vehicle is
// registered in.
export function PassedToLevel2({
  areas,
  className = "",
}: {
  areas: AreaTotal[] | undefined;
  className?: string;
}) {
  const rows = areas ?? [];
  const total = rows.reduce((sum, a) => sum + a.count, 0);
  const uncovered = rows.filter((a) => !a.hasOfficer).map((a) => a.name);

  return (
    <Card className={className}>
      <CardHeading
        title="Passed to Level 2"
        subtitle={areas ? `Per area officer · this month · ${total} total` : "Loading…"}
      />
      <div className="grid gap-3 sm:grid-cols-3">
        {rows.map((area) => {
          const share = total === 0 ? 0 : Math.round((area.count / total) * 100);
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
      {areas && (
        <Note tone="rose">
          Area rule: the officer is chosen from the area where the vehicle is registered.
          {uncovered.length > 0 &&
            ` ${uncovered.join(" and ")} has no active Level 2 officer, so complaints for ${uncovered.length === 1 ? "it" : "them"} cannot be forwarded until one is assigned.`}
        </Note>
      )}
    </Card>
  );
}
