import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, muted } from "@/components/dashboard/ui";
import type { Count, DashboardOverview } from "./types";

// Darkest for the busiest medium, lighter for each one after it.
const SHADES = ["#650720", "#8f0e2a", "#b3112f", "#d4546d", "#e8a3b2", "#f4d3da"];

// Where this officer's complaints of the month came from: the medium each one reached SPRPTA by.
export function ComplaintSources({
  sources,
  busiest,
  className = "",
}: {
  sources: Count[] | undefined;
  busiest: DashboardOverview["busiestWeek"] | undefined;
  className?: string;
}) {
  const rows = sources ?? [];
  const total = rows.reduce((sum, s) => sum + s.count, 0);
  const share = (count: number) => (total === 0 ? "0%" : `${Math.round((count / total) * 100)}%`);

  return (
    <Card className={className}>
      <CardHeading
        title="Where complaints come from"
        subtitle={sources ? `By medium · this month · ${total} total` : "Loading…"}
      />
      {sources && rows.length === 0 ? (
        <p className={muted}>You have not entered a complaint this month yet.</p>
      ) : (
        <>
          <div className="flex h-3 gap-0.5 overflow-hidden rounded-full" role="img" aria-label="Share of complaints by medium">
            {rows.map((s, i) => (
              <div key={s.label} style={{ width: share(s.count), background: SHADES[Math.min(i, SHADES.length - 1)] }} />
            ))}
          </div>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {rows.map((s, i) => (
              <li key={s.label} className="flex items-center gap-2.5 text-[0.81rem]">
                <span
                  aria-hidden="true"
                  className="size-[0.55rem] rounded-full"
                  style={{ background: SHADES[Math.min(i, SHADES.length - 1)] }}
                />
                <span className="flex-1 font-bold">{s.label}</span>
                <span className={muted}>{share(s.count)}</span>
                <b className="w-8 text-right font-extrabold tabular-nums">{s.count}</b>
              </li>
            ))}
          </ul>
        </>
      )}
      {busiest && (
        <Note className="mt-auto">
          {busiest.medium
            ? `This week ${busiest.medium} is the busiest medium, ${busiest.count} of ${busiest.total} complaints.`
            : "Nothing entered this week yet."}
        </Note>
      )}
    </Card>
  );
}
