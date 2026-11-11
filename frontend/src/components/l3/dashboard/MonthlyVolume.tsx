import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading } from "@/components/dashboard/ui";
import type { MonthVolume } from "./types";

// Complaints received and closed in each of the last months, as pairs of bars.
export function MonthlyVolume({ months, className = "" }: { months: MonthVolume[]; className?: string }) {
  const busiest = Math.max(...months.map((m) => m.received));
  const first = months[0];
  const last = months[months.length - 1];
  const rates = months.map((m) => Math.round((m.closed / m.received) * 100));
  const growth = Math.round(((last.received - first.received) / first.received) * 100);

  return (
    <Card className={className}>
      <CardHeading title="Complaints per month" subtitle={`Last ${months.length} months · all areas`} />
      <div className="flex gap-3.5 text-[0.75rem] font-bold">
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="size-[0.55rem] rounded-full bg-[#f0b8c4]" />
          Received
        </span>
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="size-[0.55rem] rounded-full bg-crimson" />
          Closed
        </span>
      </div>
      <div
        className="grid h-[11rem] grid-cols-6 gap-2.5"
        role="img"
        aria-label={`Complaints received and closed each month, ${first.label} to ${last.label}`}
      >
        {months.map((m) => (
          <div key={m.label} className="flex min-w-0 flex-col items-center justify-end gap-1.5">
            <div className="flex h-full items-end gap-1">
              <div className="w-3.5 rounded-t-md bg-[#f0b8c4]" style={{ height: `${(m.received / busiest) * 100}%` }} />
              <div className="w-3.5 rounded-t-md bg-crimson" style={{ height: `${(m.closed / busiest) * 100}%` }} />
            </div>
            <span className="text-[0.72rem] font-bold text-muted">{m.label}</span>
          </div>
        ))}
      </div>
      <Note className="mt-auto">
        <b className="font-extrabold text-ink">Volume up {growth}%</b> since {first.label}. The closure rate stayed
        between {Math.min(...rates)}% and {Math.max(...rates)}%.
      </Note>
    </Card>
  );
}
