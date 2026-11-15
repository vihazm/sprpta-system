import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, Chip, PillLink, muted } from "@/components/dashboard/ui";
import { ageText } from "@/components/l1/status";
import type { PortalSubmission } from "./types";

// Complaints the public sent through the portal. Level 1 checks each one before it goes on.
export function PortalQueue({
  submissions,
  waiting,
  loaded,
  className = "",
}: {
  submissions: PortalSubmission[];
  waiting: number; // how many are in the queue, which can be more than the few listed here
  loaded: boolean;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeading
        title="Portal submissions"
        subtitle="Awaiting your check"
        action={<Chip tone="brand">{loaded ? `${waiting} waiting` : "Loading…"}</Chip>}
      />
      {loaded && submissions.length === 0 && (
        <p className={muted}>No portal submissions are waiting. They appear here as complainants send them.</p>
      )}
      <ul className="m-0 flex list-none flex-col p-0">
        {submissions.map((s) => (
          <li key={s.id} className="flex items-center gap-3 border-t border-[#f1ebed] py-2.5 first:border-t-0 first:pt-0">
            <div className="min-w-0 flex-1">
              <p className="truncate text-[0.81rem] font-extrabold">{s.title}</p>
              <p className={muted}>
                {s.complainant ?? "Name not given"} · {ageText(s.ageMinutes)} ago
              </p>
            </div>
            <PillLink href="/l1/portal-submissions">Review</PillLink>
          </li>
        ))}
      </ul>
      <Note className="mt-auto">
        Check the vehicle and set the severity. Then forward, keep it incomplete or reject it.
      </Note>
    </Card>
  );
}