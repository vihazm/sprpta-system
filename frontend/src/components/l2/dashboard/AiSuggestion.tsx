import { Icon } from "@/components/dashboard/icons";
import { Chip, PillButton, eyebrow, muted } from "@/components/dashboard/ui";
import type { ReviewedCase } from "./types";

// The AI's advice for the case, with the policy clauses it is based on (UC-L2-03).
// It is advisory only: the officer decides, and the case can be handled without it.
export function AiSuggestion({ ai }: { ai: ReviewedCase["ai"] }) {
  return (
    <div className="flex flex-col gap-3 rounded-3xl border-[1.5px] border-[#efc9d1] bg-[#fbf0f2] p-[1.1rem]">
      <div className="flex flex-wrap items-center gap-3">
        <span className="flex size-9 flex-none items-center justify-center rounded-xl bg-crimson text-white">
          <Icon name="sparkle" size={18} />
        </span>
        <div className="min-w-[12rem] flex-1">
          <p className="text-[0.88rem] font-extrabold">AI suggestion</p>
          <p className={muted}>Based on the active policy documents. Advisory only, you decide.</p>
        </div>
        <Chip tone="ok">Ready in {ai.readyIn}</Chip>
      </div>
      <p className="text-[0.84rem] leading-[1.55]">
        <b className="font-extrabold">Suggested action:</b> {ai.suggestion}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`${eyebrow} mr-0.5`}>Cited clauses</span>
        {ai.clauses.map((clause) => (
          <span
            key={clause}
            className="rounded-[0.65rem] border border-[#ecd2d8] bg-white px-2.5 py-1 text-[0.75rem] font-bold text-slate-600"
          >
            {clause}
          </span>
        ))}
      </div>
      <div className="flex flex-wrap gap-2.5">
        <PillButton className="!border-crimson !text-crimson-hover">Use this suggestion</PillButton>
        <PillButton>Ask again with more detail</PillButton>
      </div>
      <p className={muted}>
        Personal details are removed before the case is sent to the AI. If the service is slow or down you will see a
        message, and you can decide without it.
      </p>
    </div>
  );
}
