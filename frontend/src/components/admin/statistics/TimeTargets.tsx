import { Card, CardHeading, Chip, muted, type Tone } from "@/components/dashboard/ui";
import { Note } from "@/components/dashboard/Note";
import type { Stage, Statistics } from "./api";

const th = "px-2.5 py-1 text-left text-[0.69rem] font-bold uppercase tracking-[0.07em] text-muted";

function tone(share: number): Tone {
  return share >= 90 ? "ok" : share >= 70 ? "warn" : "crit";
}

function StageCell({ stage }: { stage: Stage }) {
  const target = stage.targetDays === null ? null : `target ${stage.targetDays} d`;
  if (stage.finished === 0) {
    return (
      <div className="flex flex-col gap-1">
        <span className="text-muted">None yet</span>
        {target && <span className={muted}>{target}</span>}
      </div>
    );
  }
  const share = Math.round((stage.onTime / stage.finished) * 100);
  return (
    <div className="flex flex-col items-start gap-1">
      <Chip tone={tone(share)}>{share}% on time</Chip>
      <span className={muted}>
        {stage.onTime} of {stage.finished} · avg {stage.averageDays} d{target && ` · ${target}`}
      </span>
    </div>
  );
}

// How long complaints took to be forwarded, decided and closed, against each severity's time target.
export function TimeTargets({ stats, className = "" }: { stats: Statistics; className?: string }) {
  return (
    <Card className={className}>
      <CardHeading
        title="Time targets"
        subtitle="Calendar days from registration, without the time a complaint spent Incomplete"
      />
      <div className="overflow-x-auto">
        <table className="w-full border-separate border-spacing-y-1 text-[0.81rem]">
          <thead>
            <tr>
              <th className={th}>Severity</th>
              <th className={th}>Forward by</th>
              <th className={th}>Decide by</th>
              <th className={th}>Close by</th>
            </tr>
          </thead>
          <tbody>
            {stats.timeTargets.map((row, i) => {
              const all = i === stats.timeTargets.length - 1;
              return (
                <tr key={row.severity} className={`*:px-2.5 *:py-2.5 *:align-top ${all ? "*:bg-[#f7f4f5]" : ""} *:first:rounded-l-[1.1rem] *:last:rounded-r-[1.1rem]`}>
                  <td className="font-extrabold">{row.severity}</td>
                  <td>
                    <StageCell stage={row.forward} />
                  </td>
                  <td>
                    <StageCell stage={row.decide} />
                  </td>
                  <td>
                    <StageCell stage={row.close} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Note tone={stats.overdue.total > 0 ? "alert" : "good"} className="mt-auto">
        {stats.overdue.total > 0
          ? `Overdue now: ${stats.overdue.awaitingDecision} past decide-by and ${stats.overdue.awaitingClose} past close-by.`
          : "No open case is past its time target."}
      </Note>
    </Card>
  );
}
