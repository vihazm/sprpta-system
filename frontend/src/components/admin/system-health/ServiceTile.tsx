import { AreaChart } from "../dashboard/AreaChart";
import type { Tone } from "../dashboard/types";
import { Card, CardHeading, Chip, StatusDot, bigNumber, muted } from "../dashboard/ui";
import type { ServiceMetric } from "./types";

const TREND_COLOR: Record<Tone, string> = {
  ok: "text-emerald-500",
  warn: "text-amber-500",
  crit: "text-red-500",
  info: "text-slate-400",
};

const TINT: Partial<Record<Tone, string>> = { warn: "!bg-amber-50", crit: "!bg-red-50" };

// One service: its status, its latest reading and how that reading has moved.
export function ServiceTile({ metric, className = "" }: { metric: ServiceMetric; className?: string }) {
  return (
    <Card className={`${TINT[metric.tone] ?? ""} ${className}`}>
      <CardHeading
        title={metric.name}
        action={
          <Chip tone={metric.tone}>
            <StatusDot tone={metric.tone} />
            {metric.status}
          </Chip>
        }
      />
      <p className={`${bigNumber} text-[2.75rem]`}>
        {metric.value}
        <span className="ml-1.5 text-[1.1rem] font-bold text-muted">{metric.unit}</span>
      </p>
      {metric.trend.length > 1 ? (
        <AreaChart
          values={metric.trend}
          label={`${metric.name}, recent response times`}
          className={`h-10 ${TREND_COLOR[metric.tone]}`}
        />
      ) : (
        <p className={`${muted} flex h-10 items-center`}>Collecting readings…</p>
      )}
      <p className={muted}>{metric.note}</p>
    </Card>
  );
}
