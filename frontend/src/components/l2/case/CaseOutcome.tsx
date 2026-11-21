import { Icon } from "@/components/dashboard/icons";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, muted } from "@/components/dashboard/ui";
import { solutionDocumentUrl } from "../api";
import { ACTION_LABEL, dateTime, OUTCOME_LABEL } from "../format";
import type { CaseDetail } from "../types";

// What was decided on a case that is past the decision step. Read-only.
export function CaseOutcome({ c }: { c: CaseDetail }) {
  if (c.escalation) {
    return (
      <Card>
        <CardHeading title="Escalated to Level 3" subtitle={`By ${c.escalation.escalatedBy} · ${dateTime(c.escalation.escalatedAt)}`} />
        <p className="whitespace-pre-line text-[0.86rem] leading-[1.6]">
          <b className="font-extrabold">Reason.</b> {c.escalation.reason}
        </p>
        <Note>Level 3 decides this case now. It is read-only for you.</Note>
      </Card>
    );
  }

  const decision = c.decision;
  const document = c.solutionDocument;
  return (
    <Card>
      <CardHeading
        title="Decision and solution"
        subtitle={decision ? `Decided by ${decision.decidedBy} · ${dateTime(decision.decidedAt)}` : undefined}
      />
      {decision && (
        <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-3 rounded-[1.25rem] bg-[#f7f4f5] p-4">
          <div>
            <dt className="text-[0.69rem] font-bold text-muted">Action</dt>
            <dd className="m-0 mt-0.5 text-[0.81rem] font-extrabold">{ACTION_LABEL[decision.action]}</dd>
          </div>
          <div>
            <dt className="text-[0.69rem] font-bold text-muted">Outcome</dt>
            <dd className="m-0 mt-0.5 text-[0.81rem] font-extrabold">{OUTCOME_LABEL[decision.outcome]}</dd>
          </div>
          <div className="col-span-2">
            <dt className="text-[0.69rem] font-bold text-muted">Reasoning</dt>
            <dd className="m-0 mt-0.5 whitespace-pre-line text-[0.84rem] leading-[1.55]">{decision.reasoning}</dd>
          </div>
        </dl>
      )}

      {document && (
        <div className="flex flex-wrap items-center gap-3.5 rounded-[1.25rem] border-[1.5px] border-dashed border-[#e3c5cb] px-4 py-3.5">
          <span className="flex size-[2.3rem] flex-none items-center justify-center rounded-xl bg-field text-slate-600">
            <Icon name="file" size={18} />
          </span>
          <div className="min-w-[14rem] flex-1">
            <p className="text-[0.84rem] font-extrabold">Solution document (PDF)</p>
            <p className={muted}>
              Created by {document.generatedBy} · {dateTime(document.generatedAt)}
            </p>
            {document.details && <p className="mt-1 whitespace-pre-line text-[0.81rem]">{document.details}</p>}
          </div>
          <a
            href={solutionDocumentUrl(c.id)}
            target="_blank"
            rel="noopener"
            className="focus-ring inline-flex h-[2.1rem] items-center gap-[0.45rem] rounded-full border-[1.5px] border-crimson bg-crimson px-[0.95rem] text-[0.78rem] font-bold text-white transition-colors hover:bg-crimson-hover"
          >
            <Icon name="download" size={13} />
            Open PDF
          </a>
        </div>
      )}

      {c.status === "awaiting_implementation" && (
        <Note>Waiting for the implementing staff to carry out the solution and mark the case as done.</Note>
      )}
      {c.status === "done_awaiting_approval" && (
        <Note tone="good">Marked as done by the implementing staff. Approving and closing comes with the implementing staff portal.</Note>
      )}
      {c.status === "closed" && <Note>This case is closed. A closed case is never reopened.</Note>}
    </Card>
  );
}
