import { bigNumber } from "@/components/dashboard/ui";
import { STATUS_LABEL, STATUS_ORDER, STATUS_STYLE } from "../status";
import type { CaseFilter, CaseStatus } from "../types";

const NOTE: Record<CaseStatus, string> = {
  forwarded: "not opened yet",
  under_review: "being decided",
  awaiting_implementation: "with implementing staff",
  done_awaiting_approval: "waiting for approval",
  escalated: "with Level 3",
  closed: "all time",
};

// The area's cases counted by status (UC-L2-01). Press a tile to filter the list by it, press it again to clear.
export function StatusTiles({
  counts,
  active,
  onPick,
}: {
  counts: Record<string, number>;
  active: CaseFilter | null;
  onPick: (status: CaseStatus) => void;
}) {
  return (
    <section aria-label="Cases by status" className="grid grid-cols-2 gap-3 min-[700px]:grid-cols-3 min-[1200px]:grid-cols-6">
      {STATUS_ORDER.map((status) => (
        <button
          key={status}
          type="button"
          aria-pressed={active === status}
          onClick={() => onPick(status)}
          className={`focus-ring flex cursor-pointer flex-col gap-0.5 rounded-[1.25rem] border-[1.5px] px-4 py-3.5 text-left transition-transform duration-150 hover:-translate-y-0.5 ${STATUS_STYLE[status]} ${
            active === status ? "border-crimson" : "border-transparent"
          }`}
        >
          <span className="min-h-[1.9rem] text-[0.75rem] font-bold leading-[1.25] text-ink">{STATUS_LABEL[status]}</span>
          <span className={`${bigNumber} text-[2.1rem] text-ink`}>{counts[status] ?? 0}</span>
          <span className="text-[0.69rem] font-bold">{NOTE[status]}</span>
        </button>
      ))}
    </section>
  );
}
