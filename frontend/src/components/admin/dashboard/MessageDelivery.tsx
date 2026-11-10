import type { AdminDashboardData } from "./types";
import { Card, CardHeading, Chip } from "./ui";

export function MessageDelivery({
  messages,
  className = "",
}: {
  messages: AdminDashboardData["messages"];
  className?: string;
}) {
  const total = messages.sent + messages.failed;
  const sentDegrees = (messages.sent / total) * 360;

  return (
    <Card className={`gap-3 ${className}`}>
      <CardHeading title="Messages" subtitle="SMS and email, 24 hours" />

      <div className="flex items-center gap-[0.9rem]">
        <div
          className="flex size-[5.75rem] flex-none items-center justify-center rounded-full"
          style={{
            background: `conic-gradient(#10b981 0deg ${sentDegrees}deg, #ef4444 ${sentDegrees}deg 360deg)`,
          }}
        >
          <div className="flex size-[4.25rem] items-center justify-center rounded-full bg-white">
            <span className="font-display text-[1.4rem] tabular-nums">
              {Math.round((messages.sent / total) * 100)}%
            </span>
          </div>
        </div>
        <div className="flex flex-col items-start gap-[0.4rem]">
          <p className="text-[0.8rem] font-bold">
            {messages.sent} of {total} sent
          </p>
          {messages.failed > 0 && <Chip tone="warn">{messages.failed} failed</Chip>}
        </div>
      </div>

      <ul className="flex list-none flex-col p-0">
        {messages.byType.map((type) => (
          <li
            key={type.label}
            className="flex items-center gap-3 border-t border-slate-100 py-[0.4rem] first:border-t-0 first:pt-0"
          >
            <span className="flex-1 text-[0.78rem] font-semibold">{type.label}</span>
            <span className="font-display text-[0.95rem] tabular-nums">{type.count}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
