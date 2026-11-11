import { Card, CardHeading, Chip, PillButton, muted } from "./ui";
import { Note } from "./Note";

export type Approval = {
  ref: string;
  action: string; // the decided action, for example "Written warning"
  title?: string;
  doneBy: string; // the implementing staff member who marked it done
  when: string;
  note: string; // how it was carried out
};

// Cases whose decided action was marked done by implementing staff. Only Approve closes a case.
export function ApprovalList({
  title,
  subtitle,
  badge,
  approvals,
  footnote,
  className = "",
}: {
  title: string;
  subtitle: string;
  badge?: string;
  approvals: Approval[];
  footnote: string;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeading title={title} subtitle={subtitle} action={badge && <Chip tone="ok">{badge}</Chip>} />
      <ul className="m-0 flex list-none flex-col p-0">
        {approvals.map((a) => (
          <li key={a.ref} className="flex flex-col gap-1.5 border-t border-[#f1ebed] py-3 first:border-t-0 first:pt-0">
            <div className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-2">
                <b className="text-[0.78rem] font-extrabold text-crimson-hover">{a.ref}</b>
                <Chip>{a.action}</Chip>
              </span>
              <span className={muted}>{a.when}</span>
            </div>
            {a.title && <p className="text-[0.82rem] font-bold">{a.title}</p>}
            <p className={muted}>
              <b className="font-extrabold text-ink">Done by {a.doneBy}</b>
            </p>
            <p className="rounded-[0.75rem] bg-[#f7f4f5] px-2.5 py-2 text-[0.78rem] leading-[1.4]">
              Note: {a.note}
            </p>
            <PillButton primary className="self-end">
              Approve and close
            </PillButton>
          </li>
        ))}
      </ul>
      <Note className="mt-auto">{footnote}</Note>
    </Card>
  );
}
