import { BarRows } from "@/components/dashboard/BarRows";
import { StatBox } from "@/components/dashboard/StatBox";
import { Card, CardHeading, eyebrow } from "@/components/dashboard/ui";
import { STAGE_STYLE } from "./CasesByStage";
import type { L2DashboardData } from "./types";

// The officer's own area for the month: how much came in, was solved, and how quickly.
export function AreaWorkload({
  data,
  area,
  className = "",
}: {
  data: L2DashboardData;
  area: string;
  className?: string;
}) {
  const { month, urgentSolved, averageDays } = data;
  const inProgress = data.stages.filter((s) => s.kind !== "forwarded");
  const busiest = Math.max(...inProgress.map((s) => s.count));

  return (
    <Card className={className}>
      <CardHeading title="Area workload" subtitle={`${area} area · this month`} />
      <div className="grid grid-cols-2 gap-2.5">
        <StatBox label="Closed this month" value={String(month.closed)} note={`of ${month.received} received`} />
        <StatBox label="Still open" value={String(month.open)} note={`across ${data.openStages} stages`} />
        <StatBox
          label="Urgent solved"
          value={`${urgentSolved.solved} / ${urgentSolved.total}`}
          note="Critical and High"
        />
        <StatBox label="Average time to solve" value={`${averageDays.actual} d`} note={`target ${averageDays.target} d`} />
      </div>
      <p className={eyebrow}>Open cases by stage</p>
      <BarRows
        labelWidth="9.6rem"
        items={inProgress.map((s) => ({
          label: s.label,
          value: s.count,
          share: (s.count / busiest) * 100,
          color: STAGE_STYLE[s.kind].bar,
        }))}
      />
    </Card>
  );
}
