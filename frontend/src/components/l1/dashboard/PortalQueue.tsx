import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, Chip, PillButton, muted } from "@/components/dashboard/ui";
import type { PortalSubmission } from "./types";

// Complaints the public sent through the portal. Level 1 checks each one before it goes on.
export function PortalQueue({
  submissions,
  className = "",
}: {
  submissions: PortalSubmission[];
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeading
        title="Portal submissions"
        subtitle="Awaiting your check"
        action={<Chip tone="brand">{submissions.length} waiting</Chip>}
      />
      <ul className="m-0 flex list-none flex-col p-0">
        {submissions.map((s) => (
          <li key={s.title} className="flex items-center gap-3 border-t border-[#f1ebed] py-2.5 first:border-t-0 first:pt-0">
            <div className="min-w-0 flex-1">
              <p className="text-[0.81rem] font-extrabold">{s.title}</p>
              <p className={muted}>{s.meta}</p>
            </div>
            <PillButton>Review</PillButton>
          </li>
        ))}
      </ul>
      <Note className="mt-auto">
        Check the vehicle and set the severity. Then forward, keep it incomplete or reject it.
      </Note>
    </Card>
  );
}
