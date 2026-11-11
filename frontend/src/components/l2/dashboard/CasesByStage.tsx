import { Card, CardHeading, bigNumber, muted } from "@/components/dashboard/ui";
import type { StageCount, StageKind } from "./types";

// A soft tile colour and a bar colour for each stage a case passes through.
export const STAGE_STYLE: Record<StageKind, { tile: string; bar: string }> = {
  forwarded: { tile: "bg-slate-100 text-slate-700", bar: "#3b475a" },
  review: { tile: "bg-sky-50 text-sky-800", bar: "#1d4f86" },
  implementation: { tile: "bg-crimson/10 text-crimson-hover", bar: "#b3112f" },
  approval: { tile: "bg-emerald-50 text-emerald-800", bar: "#1f9d63" },
  escalated: { tile: "bg-amber-50 text-amber-800", bar: "#d9a30b" },
};

export function CasesByStage({
  stages,
  area,
  className = "",
}: {
  stages: StageCount[];
  area: string;
  className?: string;
}) {
  const open = stages.reduce((sum, s) => sum + s.count, 0);

  return (
    <Card className={className}>
      <CardHeading title="Cases by stage" subtitle={`${area} area · ${open} open cases`} />
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {stages.map((s) => (
          <li key={s.kind} className={`flex items-center gap-3 rounded-[1.1rem] px-3.5 py-2.5 ${STAGE_STYLE[s.kind].tile}`}>
            <span aria-hidden="true" className="size-[0.55rem] rounded-full bg-current" />
            <b className="flex-1 text-[0.84rem] font-extrabold text-ink">{s.label}</b>
            <span className={`${bigNumber} text-[1.6rem]`}>{s.count}</span>
          </li>
        ))}
      </ul>
      <p className={muted}>Opening a forwarded case moves it to Under review.</p>
    </Card>
  );
}
