import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, muted } from "@/components/dashboard/ui";
import type { Count } from "./types";

// Darkest for the busiest medium, lighter for each one after it.
const SHADES = ["#650720", "#8f0e2a", "#b3112f", "#d4546d", "#e8a3b2", "#f4d3da"];

export function ComplaintSources({
  sources,
  busiest,
  className = "",
}: {
  sources: Count[];
  busiest: { medium: string; count: number; total: number };
  className?: string;
}) {
  const total = sources.reduce((sum, s) => sum + s.count, 0);
  const share = (count: number) => `${Math.round((count / total) * 100)}%`;

  return (
    <Card className={className}>
      <CardHeading title="Where complaints come from" subtitle={`By medium · this month · ${total} total`} />
      <div className="flex h-3 gap-0.5 overflow-hidden rounded-full" role="img" aria-label="Share of complaints by medium">
        {sources.map((s, i) => (
          <div key={s.label} style={{ width: share(s.count), background: SHADES[i] }} />
        ))}
      </div>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {sources.map((s, i) => (
          <li key={s.label} className="flex items-center gap-2.5 text-[0.81rem]">
            <span aria-hidden="true" className="size-[0.55rem] rounded-full" style={{ background: SHADES[i] }} />
            <span className="flex-1 font-bold">{s.label}</span>
            <span className={muted}>{share(s.count)}</span>
            <b className="w-8 text-right font-extrabold tabular-nums">{s.count}</b>
          </li>
        ))}
      </ul>
      <Note className="mt-auto">
        This week {busiest.medium} is the busiest medium, {busiest.count} of {busiest.total} complaints.
      </Note>
    </Card>
  );
}
