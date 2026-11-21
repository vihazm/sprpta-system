import { Note } from "@/components/dashboard/Note";
import { SeverityChip } from "@/components/dashboard/severity";
import { Card, CardHeading, Chip } from "@/components/dashboard/ui";
import { dueText } from "../format";
import type { CaseRow } from "../types";

// Cases past a time target, most overdue first. Overdue is only a flag: nothing happens automatically.
export function OverdueAlerts({
  cases,
  total,
  onOpen,
}: {
  cases: CaseRow[];
  total: number;
  onOpen: (id: number) => void;
}) {
  return (
    <Card className="gap-3">
      <CardHeading
        title="Overdue alerts"
        subtitle="Nothing happens automatically"
        action={total > 0 && <Chip tone="crit">{total} overdue</Chip>}
      />
      {cases.length === 0 && <Note tone="good">No case is past its time target.</Note>}
      {cases.map((c) => (
        <button
          key={c.id}
          type="button"
          onClick={() => onOpen(c.id)}
          className="focus-ring flex cursor-pointer flex-col gap-0.5 rounded-2xl bg-red-50 px-3.5 py-3 text-left transition-colors hover:bg-red-100/70"
        >
          <span className="flex items-center justify-between gap-2">
            <b className="text-[0.75rem] font-extrabold text-crimson-hover">{c.reference}</b>
            <SeverityChip severity={c.severity} />
          </span>
          <span className="text-[0.81rem] font-bold leading-[1.3]">{c.subject ?? "No subject"}</span>
          <span suppressHydrationWarning className="text-[0.75rem] font-extrabold text-red-800">
            {dueText(c)}
          </span>
        </button>
      ))}
      {total > cases.length && <p className="text-[0.75rem] font-bold text-muted">and {total - cases.length} more</p>}
    </Card>
  );
}
