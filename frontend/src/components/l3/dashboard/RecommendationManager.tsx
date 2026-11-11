import { inputClass } from "@/components/dashboard/controls";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, Chip, LinkButton, PillButton, muted } from "@/components/dashboard/ui";
import type { Count, RecommendationToManage } from "./types";

const STATUSES = [
  "New",
  "Acknowledged",
  "Under consideration",
  "Accepted or implemented",
  "Declined",
  "Commendation verified",
];

const STATUS_TONE = {
  New: "info",
  Acknowledged: "ok",
  "Under consideration": "warn",
  "Accepted or implemented": "ok",
  Declined: "crit",
  "Commendation verified": "brand",
} as const;

// The recommendation register, where only Level 3 changes a status (UC-L3-03).
export function RecommendationManager({
  statuses,
  items,
  className = "",
}: {
  statuses: Count[];
  items: RecommendationToManage[];
  className?: string;
}) {
  const total = statuses.reduce((sum, s) => sum + s.count, 0);

  return (
    <Card className={className}>
      <CardHeading
        title="Recommendations"
        subtitle="Entered by Level 1 · only you change their status"
        action={<LinkButton>See all {total}</LinkButton>}
      />
      <div className="flex flex-wrap gap-1.5">
        {statuses.map((s) => (
          <Chip key={s.label} tone={STATUS_TONE[s.label as keyof typeof STATUS_TONE]}>
            {s.label} · {s.count}
          </Chip>
        ))}
      </div>
      <ul className="m-0 flex list-none flex-col p-0">
        {items.map((item) => (
          <li
            key={item.ref}
            className="flex flex-wrap items-center gap-3 border-t border-[#f1ebed] py-2.5 first:border-t-0 first:pt-0"
          >
            <div className="min-w-[14rem] flex-[1_1_14rem]">
              <p className="text-[0.81rem] font-extrabold">{item.title}</p>
              <p className={muted}>
                {item.ref} · {item.kind} · entered by {item.enteredBy}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <label className="sr-only" htmlFor={`status-${item.ref}`}>
                Status of {item.ref}
              </label>
              <select
                id={`status-${item.ref}`}
                className={`${inputClass} !h-[2.1rem] !w-[12rem] !rounded-full !text-[0.78rem] font-bold`}
                defaultValue={item.status}
              >
                {STATUSES.map((status) => (
                  <option key={status}>{status}</option>
                ))}
              </select>
              <PillButton>Update</PillButton>
            </div>
          </li>
        ))}
      </ul>
      <Note>A commendation counts toward a rating only after you mark it Commendation verified.</Note>
    </Card>
  );
}
