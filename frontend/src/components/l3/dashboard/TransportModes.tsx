import { Card, CardHeading, muted } from "@/components/dashboard/ui";
import type { TransportMode } from "./types";

export function TransportModes({ modes, className = "" }: { modes: TransportMode[]; className?: string }) {
  return (
    <Card className={className}>
      <CardHeading title="Bus and trishaw" subtitle="By transport mode" />
      {modes.map((mode) => (
        <div key={mode.label} className="flex flex-col gap-2 rounded-[1.25rem] bg-[#f7f4f5] p-4">
          <div className="flex justify-between">
            <b className="text-[0.94rem] font-extrabold">{mode.label}</b>
            <span className={muted}>{mode.cases} cases</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-[#ece4e7]">
            <div className="h-full rounded-full" style={{ width: `${mode.closedPercent}%`, background: mode.color }} />
          </div>
          <div className={`flex justify-between ${muted}`}>
            <span>Closed {mode.closedPercent}%</span>
            <span>Average time {mode.averageDays} d</span>
          </div>
        </div>
      ))}
      <p className={`${muted} mt-auto`}>
        Trishaw complaints close slower, mostly because owners are harder to trace.
      </p>
    </Card>
  );
}
