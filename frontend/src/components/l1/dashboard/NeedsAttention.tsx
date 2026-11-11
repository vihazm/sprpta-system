import { Icon, type IconName } from "@/components/dashboard/icons";
import { Card, CardHeading, Chip, LinkButton, bigNumber, eyebrow } from "@/components/dashboard/ui";
import type { QueueCount, QueueKind, WaitingCase } from "./types";

const QUEUE_STYLE: Record<QueueKind, { icon: IconName; tile: string }> = {
  portal: { icon: "inbox", tile: "bg-crimson/10 text-crimson-hover" },
  drafts: { icon: "clock", tile: "bg-slate-100 text-slate-700" },
  incomplete: { icon: "warning", tile: "bg-amber-50 text-amber-900" },
  duplicates: { icon: "copy", tile: "bg-orange-50 text-orange-800" },
};

const STATUS_TONE = { Draft: "info", Incomplete: "warn", "Possible duplicate": "brand" } as const;

// What is waiting for Level 1: the queues and the oldest items in them.
export function NeedsAttention({
  queues,
  waiting,
  className = "",
}: {
  queues: QueueCount[];
  waiting: WaitingCase[];
  className?: string;
}) {
  const open = queues.reduce((sum, q) => sum + q.count, 0);

  return (
    <Card className={className}>
      <CardHeading title="Needs attention" subtitle={`${open} open items, oldest first`} />
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {queues.map((q) => (
          <li key={q.kind} className={`flex items-center gap-3 rounded-[1.25rem] px-4 py-3 ${QUEUE_STYLE[q.kind].tile}`}>
            <span className="flex size-[2.4rem] flex-none items-center justify-center rounded-xl bg-white">
              <Icon name={QUEUE_STYLE[q.kind].icon} size={19} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[0.88rem] font-extrabold text-ink">{q.title}</p>
              <p className="text-[0.75rem] text-muted">{q.note}</p>
            </div>
            <span className={`${bigNumber} text-[1.9rem]`}>{q.count}</span>
          </li>
        ))}
      </ul>

      <p className={`${eyebrow} mt-1`}>Waiting longest</p>
      <ul className="m-0 flex list-none flex-col p-0">
        {waiting.map((w) => (
          <li
            key={`${w.ref}-${w.title}`}
            className="grid grid-cols-[6.5rem_minmax(0,1fr)_auto_2.2rem] items-center gap-2.5 border-t border-[#f1ebed] py-2 text-[0.78rem] first:border-t-0"
          >
            <b className="text-[0.75rem] font-extrabold text-crimson-hover">{w.ref ?? "No reference"}</b>
            <span className="truncate font-semibold">{w.title}</span>
            <Chip tone={STATUS_TONE[w.status]}>{w.status}</Chip>
            <span className="text-right text-muted">{w.age}</span>
          </li>
        ))}
      </ul>
      <div className="self-end">
        <LinkButton>Open all complaints</LinkButton>
      </div>
    </Card>
  );
}
