import { Card, CardHeading, Chip, StatusDot, muted } from "@/components/dashboard/ui";
import { formatEventTime } from "./format";
import type { HealthEvent } from "./types";

export function RecentEvents({ events, className = "" }: { events: HealthEvent[]; className?: string }) {
  return (
    <Card className={className}>
      <CardHeading
        title="Recent events"
        subtitle="Services changing state, and anything happening to accounts"
        action={<Chip>{events.length} events</Chip>}
      />
      {events.length === 0 ? (
        <p className={muted}>Nothing to report yet. Events appear when a service changes state.</p>
      ) : (
        <ul className="m-0 flex list-none flex-col p-0">
          {events.map((event) => (
            <li
              key={`${event.occurredAt}-${event.title}`}
              className="flex items-start gap-3 border-t border-[#f1ebed] py-2.5 first:border-t-0 first:pt-0 last:pb-0"
            >
              <span className="mt-[0.35rem]">
                <StatusDot tone={event.tone} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[0.84rem] font-bold">{event.title}</p>
                {event.detail && <p className={muted}>{event.detail}</p>}
              </div>
              <span className={`${muted} whitespace-nowrap tabular-nums`}>
                {formatEventTime(event.occurredAt)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
