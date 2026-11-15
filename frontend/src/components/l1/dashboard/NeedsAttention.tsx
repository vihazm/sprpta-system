import Link from "next/link";
import { Icon, type IconName } from "@/components/dashboard/icons";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, Chip, PillButton, bigNumber, eyebrow, muted } from "@/components/dashboard/ui";
import { STATUS_TONE, ageText } from "@/components/l1/status";
import type { DashboardSummary, QueueKind } from "./types";

// Each card opens the list it counts. Portal submissions has its own screen; the rest are filters of Complaints.
const QUEUES: { kind: QueueKind; title: string; note: string; href: string; icon: IconName; tile: string }[] = [
  { kind: "portal", title: "Portal submissions", note: "Awaiting your check", href: "/l1/portal-submissions", icon: "inbox", tile: "bg-crimson/10 text-crimson-hover" },
  { kind: "drafts", title: "Drafts", note: "Started, no reference yet", href: "/l1/complaints?status=draft&scope=all", icon: "clock", tile: "bg-slate-100 text-slate-700" },
  { kind: "incomplete", title: "Incomplete", note: "Details missing, clock paused", href: "/l1/complaints?status=incomplete&scope=all", icon: "warning", tile: "bg-amber-50 text-amber-900" },
  { kind: "duplicates", title: "Possible duplicates", note: "Compare before forwarding", href: "/l1/complaints?status=duplicates&scope=all", icon: "copy", tile: "bg-orange-50 text-orange-800" },
];

// What is waiting for Level 1: the queues, and the oldest open cases in them.
export function NeedsAttention({
  summary,
  error,
  className = "",
  onRetry,
}: {
  summary: DashboardSummary | null;
  error: string | null;
  className?: string;
  onRetry: () => void;
}) {
  const open = summary ? summary.queues.portal + summary.queues.drafts + summary.queues.incomplete : 0;

  return (
    <Card className={className}>
      <CardHeading
        title="Needs attention"
        subtitle={summary ? `${open} open items, oldest first` : error ? "Could not load" : "Loading…"}
      />
      {error && !summary && (
        <>
          <Note tone="alert">{error}</Note>
          <PillButton className="self-start" onClick={onRetry}>
            Try again
          </PillButton>
        </>
      )}
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {QUEUES.map((q) => (
          <li key={q.kind}>
            <Link
              href={q.href}
              className={`focus-ring flex items-center gap-3 rounded-[1.25rem] px-4 py-3 transition-shadow hover:shadow-[0_0_0_1.5px_rgba(179,17,47,0.35)] ${q.tile}`}
            >
              <span className="flex size-[2.4rem] flex-none items-center justify-center rounded-xl bg-white">
                <Icon name={q.icon} size={19} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[0.88rem] font-extrabold text-ink">{q.title}</span>
                <span className="block text-[0.75rem] text-muted">{q.note}</span>
              </span>
              <span className={`${bigNumber} text-[1.9rem]`}>{summary ? summary.queues[q.kind] : "–"}</span>
            </Link>
          </li>
        ))}
      </ul>

      <p className={`${eyebrow} mt-1`}>Waiting longest</p>
      {summary && summary.waiting.length === 0 && <p className={muted}>Nothing is waiting. Every case has moved on.</p>}
      <ul className="m-0 flex list-none flex-col p-0">
        {summary?.waiting.map((w) => {
          const label = w.possibleDuplicate ? "Possible duplicate" : w.status;
          return (
            <li key={w.id} className="border-t border-[#f1ebed] first:border-t-0">
              <Link
                href={`/l1/new-complaint?id=${w.id}`}
                className="focus-ring grid grid-cols-[6.5rem_minmax(0,1fr)_auto_2.2rem] items-center gap-2.5 py-2 text-[0.78rem] hover:bg-[#fbf5f6]"
              >
                <b className="text-[0.75rem] font-extrabold text-crimson-hover">{w.reference ?? "No reference"}</b>
                <span className="truncate font-semibold">{w.title}</span>
                <Chip tone={w.possibleDuplicate ? "brand" : STATUS_TONE[w.status]}>{label}</Chip>
                <span className="text-right text-muted">{ageText(w.ageMinutes)}</span>
              </Link>
            </li>
          );
        })}
      </ul>
      <div className="self-end">
        <Link href="/l1/complaints?scope=all" className="focus-ring whitespace-nowrap text-[0.78rem] font-extrabold text-crimson-hover hover:underline">
          Open all complaints
        </Link>
      </div>
    </Card>
  );
}