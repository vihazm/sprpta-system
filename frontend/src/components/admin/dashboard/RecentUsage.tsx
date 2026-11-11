import type { UsageEvent } from "./types";
import { Card, CardHeading, PillButton, muted } from "@/components/dashboard/ui";

const DOT_STYLES: Record<UsageEvent["event"], string> = {
  "signed in": "border-crimson bg-white",
  "signed out": "border-slate-300 bg-white",
  "failed sign-in": "border-red-500 bg-red-50",
};

export function RecentUsage({ events, className = "" }: { events: UsageEvent[]; className?: string }) {
  return (
    <Card className={className}>
      <CardHeading
        title="Just now"
        subtitle="Recent usage, names masked"
        action={<PillButton>All logs</PillButton>}
      />
      <ul className="flex list-none flex-col p-0">
        {events.map((e, i) => (
          <li
            key={`${e.time}-${e.who}-${i}`}
            className="relative pb-4 pl-[1.6rem] before:absolute before:-bottom-0.5 before:left-[0.32rem] before:top-4 before:w-0.5 before:bg-slate-100 last:pb-0 last:before:hidden"
          >
            <span
              aria-hidden="true"
              className={`absolute left-0 top-1 size-3 rounded-full border-[3px] ${DOT_STYLES[e.event]}`}
            />
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-[0.85rem] font-bold">{e.who}</p>
              <span className="text-[0.75rem] tabular-nums text-muted">{e.time}</span>
            </div>
            <p className={muted}>
              {e.role}, {e.event}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
