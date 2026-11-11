import type { AttentionItem, Tone } from "./types";
import { Card, Chip, PillButton, StatusDot, TONE_BG, muted } from "@/components/dashboard/ui";

const TONE_LABEL: Record<Tone, string> = {
  crit: "Critical",
  warn: "Warning",
  info: "Notice",
  ok: "Resolved",
};

const URGENT_BOX: Record<Tone, string> = {
  crit: "bg-red-50",
  warn: "bg-amber-50",
  info: "bg-slate-100",
  ok: "bg-emerald-50",
};

function AlertIcon() {
  return (
    <svg
      width="19"
      height="19"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3l10 18H2L12 3zM12 10v5M12 18h.01" />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="flex-none text-[#9AA0AA]"
    >
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

/** The most urgent item is shown in full, the rest as a short list. */
export function NeedsAttention({ items, className = "" }: { items: AttentionItem[]; className?: string }) {
  const [urgent, ...others] = items;

  return (
    <Card className={className}>
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-[1.06rem] font-extrabold tracking-[-0.015em]">Needs you</h3>
        <Chip tone={items.length > 0 ? "crit" : "ok"}>
          {items.length > 0 ? `${items.length} open` : "All clear"}
        </Chip>
      </div>

      {urgent && (
        <div className={`flex items-start gap-[0.8rem] rounded-[1.4rem] p-4 ${URGENT_BOX[urgent.tone]}`}>
          <span
            className={`flex size-[2.4rem] flex-none items-center justify-center rounded-full text-white ${TONE_BG[urgent.tone]}`}
          >
            <AlertIcon />
          </span>
          <div className="min-w-0">
            <p className="text-[0.69rem] font-bold uppercase tracking-[0.09em] text-slate-700">
              {TONE_LABEL[urgent.tone]}
            </p>
            <p className="mt-[0.2rem] text-[0.97rem] font-extrabold leading-[1.3]">{urgent.title}</p>
            <p className={`mt-1 ${muted}`}>{urgent.detail}</p>
            {urgent.action && (
              <PillButton primary className="mt-3">
                {urgent.action}
              </PillButton>
            )}
          </div>
        </div>
      )}

      <ul className="flex list-none flex-col p-0">
        {others.map((item) => (
          <li
            key={item.title}
            className="flex items-center gap-3 border-t border-slate-100 py-[0.65rem] first:border-t-0 first:pt-0"
          >
            <StatusDot tone={item.tone} />
            <div className="min-w-0 flex-1">
              <p className="text-[0.85rem] font-bold leading-[1.3]">{item.title}</p>
              <p className={muted}>{item.detail}</p>
            </div>
            <ChevronIcon />
          </li>
        ))}
      </ul>
    </Card>
  );
}
