import { Field, inputClass } from "@/components/dashboard/controls";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, LinkButton } from "@/components/dashboard/ui";
import type { AuditEntry } from "./types";

// The read-only record of every action, with filters (UC-L3-05). Entries are added by the system only.
export function AuditTrail({ entries, className = "" }: { entries: AuditEntry[]; className?: string }) {
  return (
    <Card className={className}>
      <CardHeading
        title="Audit trail"
        subtitle="Every action with its exact server time. Read-only."
        action={<LinkButton>Open full log</LinkButton>}
      />
      <div className="grid gap-2.5 sm:grid-cols-4">
        <Field label="Case" htmlFor="audit-case">
          <input id="audit-case" className={inputClass} placeholder="C-2026-00403" />
        </Field>
        <Field label="User" htmlFor="audit-user">
          <select id="audit-user" className={inputClass}>
            <option>Anyone</option>
            <option>Chaminda R.</option>
            <option>Nadeesha K.</option>
          </select>
        </Field>
        <Field label="Action" htmlFor="audit-action">
          <select id="audit-action" className={inputClass}>
            <option>Any action</option>
            <option>Status change</option>
            <option>Decision</option>
            <option>Escalation</option>
          </select>
        </Field>
        <Field label="Date" htmlFor="audit-date">
          <select id="audit-date" className={inputClass}>
            <option>Today</option>
            <option>Last 7 days</option>
            <option>This month</option>
          </select>
        </Field>
      </div>
      <ul className="m-0 flex list-none flex-col p-0">
        {entries.map((e) => (
          <li
            key={`${e.time}-${e.ref}`}
            className="grid grid-cols-[4.4rem_7rem_minmax(0,1fr)] items-baseline gap-3 border-t border-[#f1ebed] py-2.5 text-[0.78rem] first:border-t-0 first:pt-0"
          >
            <span className="font-semibold tabular-nums text-muted">{e.time}</span>
            <span className="font-extrabold">{e.user}</span>
            <span className="text-slate-700">
              {e.text} <b className="font-extrabold text-crimson-hover">{e.ref}</b>
            </span>
          </li>
        ))}
      </ul>
      <Note>Entries are added by the system only. They cannot be edited or deleted by anyone.</Note>
    </Card>
  );
}
