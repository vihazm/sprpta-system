import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, Chip, PillButton, muted } from "@/components/dashboard/ui";
import type { Appeal } from "./types";

// Appeals against a rating (UC-L3-06 and UC-L3-08): correct an outcome or move a complaint
// to the right person, and the rating is recalculated.
export function RatingAppeals({ appeals, className = "" }: { appeals: Appeal[]; className?: string }) {
  return (
    <Card className={className}>
      <CardHeading
        title="Rating appeals"
        subtitle="Correct an outcome or move a complaint to the right person"
        action={<Chip tone="warn">{appeals.length} open</Chip>}
      />
      <ul className="m-0 flex list-none flex-col p-0">
        {appeals.map((a) => (
          <li key={a.title} className="flex flex-col gap-2 border-t border-[#f1ebed] py-3 first:border-t-0 first:pt-0">
            <div className="flex items-center justify-between gap-2">
              <b className="text-[0.84rem] font-extrabold">{a.title}</b>
              <span className={muted}>{a.when}</span>
            </div>
            <p className={muted}>{a.detail}</p>
            <div className="flex flex-wrap gap-2">
              <PillButton className="!border-crimson !text-crimson-hover">Review complaints</PillButton>
              <PillButton>{a.action}</PillButton>
            </div>
          </li>
        ))}
      </ul>
      <Note className="mt-auto">
        After a change the system recalculates the rating and the result is recorded in the audit trail.
      </Note>
    </Card>
  );
}
