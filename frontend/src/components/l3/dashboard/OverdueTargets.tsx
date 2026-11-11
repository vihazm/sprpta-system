import { BarRows } from "@/components/dashboard/BarRows";
import { SeverityChip } from "@/components/dashboard/severity";
import { Card, CardHeading, Chip, LinkButton, eyebrow, muted } from "@/components/dashboard/ui";
import type { L3DashboardData } from "./types";

// A bar is green from 90% on time, amber below that.
const onTimeColor = (percent: number) => (percent >= 90 ? "#1f9d63" : "#d9a30b");

// Cases past a time target anywhere in the system, and how well the targets are being met.
export function OverdueTargets({
  data,
  className = "",
}: {
  data: Pick<L3DashboardData, "overdue" | "onTime" | "month">;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeading
        title="Overdue and time targets"
        subtitle="System-wide alerts. Nothing happens automatically."
        action={<Chip tone="crit">{data.month.overdue} overdue</Chip>}
      />
      <ul className="m-0 flex list-none flex-col p-0">
        {data.overdue.map((c) => (
          <li key={c.ref} className="flex items-center gap-3 border-t border-[#f1ebed] py-2.5 first:border-t-0 first:pt-0">
            <b className="w-[6.5rem] text-[0.75rem] font-extrabold text-crimson-hover">{c.ref}</b>
            <div className="min-w-0 flex-1">
              <p className="text-[0.81rem] font-bold">{c.title}</p>
              <p className={muted}>
                {c.area} · {c.step}
              </p>
            </div>
            <SeverityChip severity={c.severity} />
            <b className="w-[5.7rem] text-right text-[0.75rem] font-extrabold text-red-800">{c.overdueBy}</b>
          </li>
        ))}
      </ul>

      <p className={`${eyebrow} mt-0.5`}>On time this month</p>
      <BarRows
        labelWidth="7.8rem"
        unit="%"
        items={data.onTime.map((t) => ({
          label: t.label,
          value: t.percent,
          share: t.percent,
          color: onTimeColor(t.percent),
        }))}
      />
      <div className="self-end">
        <LinkButton>See all {data.month.overdue} overdue cases</LinkButton>
      </div>
    </Card>
  );
}
