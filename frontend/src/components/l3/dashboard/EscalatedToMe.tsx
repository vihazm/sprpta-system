import { Note } from "@/components/dashboard/Note";
import { SeverityChip } from "@/components/dashboard/severity";
import { Card, CardHeading, Chip, LinkButton, PillButton, muted } from "@/components/dashboard/ui";
import type { EscalatedCase } from "./types";

// Cases Level 2 could not resolve. The officer's reason is always shown.
export function EscalatedToMe({
  cases,
  total,
  className = "",
}: {
  cases: EscalatedCase[];
  total: number;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeading
        title="Escalated to me"
        subtitle={`${total} cases from Level 2 · the officer's reason is always shown`}
        action={<LinkButton>See all {total}</LinkButton>}
      />
      <ul className="m-0 flex list-none flex-col gap-3 p-0">
        {cases.map((c) => (
          <li key={c.ref} className="flex flex-col gap-2 rounded-[1.4rem] bg-[#f7f4f5] px-[1.1rem] py-4">
            <div className="flex flex-wrap items-center gap-2.5">
              <b className="text-[0.81rem] font-extrabold text-crimson-hover">{c.ref}</b>
              <SeverityChip severity={c.severity} />
              <Chip>Escalated</Chip>
              <span className={`${muted} ml-auto`}>Escalated {c.escalatedAgo}</span>
            </div>
            <p className="text-[0.94rem] font-extrabold">{c.title}</p>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="min-w-[16rem] flex-1 text-[0.81rem] leading-[1.45]">
                <b className="font-extrabold">Why escalated:</b> {c.reason} <span className={muted}>· {c.officer}</span>
              </p>
              <PillButton primary>Decide</PillButton>
            </div>
          </li>
        ))}
      </ul>
      <Note>
        You follow the same steps as Level 2: AI suggestion, decision, solution document, then approval once the
        implementing staff mark it done. A case cannot be sent back to Level 1 or reassigned.
      </Note>
    </Card>
  );
}
