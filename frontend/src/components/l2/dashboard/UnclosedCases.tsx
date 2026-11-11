import { BarRows } from "@/components/dashboard/BarRows";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, StatusDot, eyebrow, muted } from "@/components/dashboard/ui";
import type { L2DashboardData } from "./types";

// How long the open cases have been waiting, and the messages sent to complainants today.
export function UnclosedCases({ data, className = "" }: { data: L2DashboardData; className?: string }) {
  const open = data.ages.reduce((sum, a) => sum + a.count, 0);
  const oldest = Math.max(...data.ages.map((a) => a.count));

  return (
    <Card className={className}>
      <CardHeading title="Unclosed cases by age" subtitle={`${open} open`} />
      <BarRows
        labelWidth="5.8rem"
        items={data.ages.map((a) => ({
          label: a.label,
          value: a.count,
          share: (a.count / oldest) * 100,
          color: a.color,
        }))}
      />
      <Note tone="alert">{data.overAgeNote}</Note>

      <p className={`${eyebrow} mt-1`}>Messages to complainants today</p>
      <ul className="m-0 flex list-none flex-col p-0">
        {data.messages.map((m) => (
          <li key={m.ref} className="flex items-start gap-3 border-t border-[#f1ebed] py-2.5 first:border-t-0 first:pt-0">
            <span className="mt-1.5">
              <StatusDot tone={m.failed ? "warn" : "ok"} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[0.78rem] font-extrabold">{m.ref}</p>
              <p className={muted}>{m.text}</p>
            </div>
            <span className={`${muted} tabular-nums`}>{m.time}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
