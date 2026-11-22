import { BarRows } from "@/components/dashboard/BarRows";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, eyebrow } from "@/components/dashboard/ui";
import { OUTCOME_LABEL } from "../format";
import type { AreaStatistics as Statistics, DecisionOutcome } from "../types";

const OUTCOME_COLOR: Record<DecisionOutcome, string> = {
  substantiated: "#a8190e",
  partly_substantiated: "#d9a30b",
  not_substantiated: "#94a3b8",
};

const share = (value: number, total: number) => (total > 0 ? Math.round((value / total) * 100) : 0);

// The officer's own area over the last 12 months (statistics for Level 2 are limited to the own area).
export function AreaStatistics({ stats, area, className = "" }: { stats: Statistics; area: string; className?: string }) {
  const top = stats.categories[0]?.count ?? 0;
  const decided = Object.values(stats.outcomes).reduce((sum, n) => sum + (n ?? 0), 0);

  return (
    <Card className={className}>
      <CardHeading
        title="Your area at a glance"
        subtitle={`${stats.cases} ${stats.cases === 1 ? "case" : "cases"} forwarded to the ${area} area in the last 12 months`}
      />
      {stats.cases === 0 ? (
        <Note>No cases reached your area in the last 12 months.</Note>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          <div className="flex flex-col gap-3">
            <p className={eyebrow}>Most common complaints</p>
            <BarRows
              labelWidth="minmax(7rem,11rem)"
              items={stats.categories.map((c) => ({ label: c.name, value: c.count, share: share(c.count, top) }))}
            />
          </div>
          <div className="flex flex-col gap-3">
            <p className={eyebrow}>Outcome of decided cases</p>
            {decided === 0 ? (
              <Note>No case has a solution document yet.</Note>
            ) : (
              <BarRows
                labelWidth="10rem"
                items={(Object.keys(OUTCOME_LABEL) as DecisionOutcome[]).map((o) => ({
                  label: OUTCOME_LABEL[o],
                  value: stats.outcomes[o] ?? 0,
                  share: share(stats.outcomes[o] ?? 0, decided),
                  color: OUTCOME_COLOR[o],
                }))}
              />
            )}
          </div>
        </div>
      )}
    </Card>
  );
}
