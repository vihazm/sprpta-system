import Link from "next/link";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, Chip, muted } from "@/components/dashboard/ui";
import { ACTION_LABEL, dateTime, historyText, OUTCOME_LABEL, shortDate } from "../format";
import type { CaseDetail, HistoryEntry } from "../types";

// Earlier complaints against the same vehicle or person, with what was decided on them.
export function EarlierCases({ c }: { c: CaseDetail }) {
  return (
    <Card className="gap-3">
      <CardHeading title="Earlier complaints" subtitle="Against the same vehicle or person, in your area" />
      {c.earlier.length === 0 && <Note>No earlier complaints on record.</Note>}
      <ul className="m-0 flex list-none flex-col p-0">
        {c.earlier.map((e) => (
          <li key={e.id} className="border-t border-[#f1ebed] first:border-t-0">
            <Link
              href={`/l2/cases/${e.id}`}
              className="focus-ring -mx-2 flex flex-col gap-1 rounded-xl px-2 py-2.5 hover:bg-[#f7f4f5]"
            >
              <span className="flex items-center justify-between gap-2">
                <b className="text-[0.75rem] font-extrabold text-crimson-hover">{e.reference}</b>
                <span className={muted}>{shortDate(e.registeredAt)}</span>
              </span>
              <span className="text-[0.81rem] font-semibold">{e.subject ?? "No subject"}</span>
              <span className="flex flex-wrap gap-1.5">
                {e.action ? (
                  <>
                    <Chip tone="brand">{ACTION_LABEL[e.action]}</Chip>
                    {e.outcome && <Chip>{OUTCOME_LABEL[e.outcome]}</Chip>}
                  </>
                ) : (
                  <Chip>Not decided yet</Chip>
                )}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}

// The case's History, read from the audit trail: who did what, and when (shared component, UI Flow 7).
export function CaseHistory({ history }: { history: HistoryEntry[] }) {
  return (
    <Card className="gap-3">
      <CardHeading title="History" subtitle="From the audit trail · read-only" />
      <ol className="m-0 flex list-none flex-col p-0">
        {[...history].reverse().map((h, i) => (
          <li key={`${h.occurredAt}-${i}`} className="flex gap-3">
            <span aria-hidden="true" className="flex flex-col items-center">
              <span className="mt-1.5 size-2.5 flex-none rounded-full bg-crimson" />
              <span className="w-0.5 flex-1 bg-[#ecd2d8]" />
            </span>
            <div className="pb-3.5">
              <p className="text-[0.81rem] font-bold">{historyText(h)}</p>
              <p className={muted}>
                {h.actor ?? (h.role === "cp" ? "Complainant" : "System")} · {dateTime(h.occurredAt)}
              </p>
              {h.reason && <p className="mt-1 text-[0.78rem] leading-[1.45]">Reason: {h.reason}</p>}
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}
