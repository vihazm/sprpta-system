import { Card, CardHeading, Chip, muted } from "@/components/dashboard/ui";
import type { EscalatedCase } from "./types";

// Cases the officer passed to Level 3, each with the reason that was given.
export function EscalatedCases({ cases, className = "" }: { cases: EscalatedCase[]; className?: string }) {
  return (
    <Card className={className}>
      <CardHeading
        title="Escalated to Level 3"
        subtitle="Cases you passed on, with your reason"
        action={<Chip>{cases.length} waiting</Chip>}
      />
      <ul className="m-0 flex list-none flex-col p-0">
        {cases.map((c) => (
          <li key={c.ref} className="flex flex-col gap-1 border-t border-[#f1ebed] py-3 first:border-t-0 first:pt-0">
            <div className="flex justify-between gap-2">
              <b className="text-[0.78rem] font-extrabold text-crimson-hover">{c.ref}</b>
              <span className={muted}>{c.when}</span>
            </div>
            <p className="text-[0.81rem] font-bold">{c.title}</p>
            <p className={muted}>
              <b className="font-extrabold text-ink">Your reason:</b> {c.reason}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
