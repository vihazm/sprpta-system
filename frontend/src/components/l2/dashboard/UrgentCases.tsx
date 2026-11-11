import { Note } from "@/components/dashboard/Note";
import { SeverityChip } from "@/components/dashboard/severity";
import { Card, CardHeading, Chip } from "@/components/dashboard/ui";
import type { UrgentCase } from "./types";

// Cases in the order they need attention. The first one is the case being reviewed.
export function UrgentCases({ cases, className = "" }: { cases: UrgentCase[]; className?: string }) {
  const overdue = cases.filter((c) => c.overdue).length;

  return (
    <Card className={className}>
      <CardHeading
        title="Most urgent first"
        subtitle="Sorted by severity and time target"
        action={overdue > 0 && <Chip tone="crit">{overdue} overdue</Chip>}
      />
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {cases.map((c, i) => (
          <li
            key={c.ref}
            className={`flex flex-col gap-0.5 rounded-2xl border-[1.5px] px-3.5 py-2.5 ${
              i === 0 ? "border-crimson bg-white" : c.overdue ? "border-transparent bg-red-50" : "border-transparent bg-[#f7f4f5]"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <b className="text-[0.75rem] font-extrabold text-crimson-hover">{c.ref}</b>
              <SeverityChip severity={c.severity} />
            </div>
            <p className="text-[0.81rem] font-bold leading-[1.3]">{c.title}</p>
            <p className={`text-[0.75rem] font-extrabold ${c.overdue ? "text-red-800" : "text-slate-600"}`}>{c.due}</p>
          </li>
        ))}
      </ul>
      <Note tone="alert" className="mt-auto">
        <b className="font-extrabold">Overdue alert.</b> {overdue} {overdue === 1 ? "case is" : "cases are"} past its time target. Critical must be
        decided within 1 day, High within 3 days. Nothing happens automatically.
      </Note>
    </Card>
  );
}
