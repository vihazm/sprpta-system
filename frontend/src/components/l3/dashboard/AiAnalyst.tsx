import { inputClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { Card, Chip, PillButton, eyebrow, muted } from "@/components/dashboard/ui";
import type { AiAnswer } from "./types";

// Plain-language questions about patterns in the complaints. This is an optional extra
// ("Could" in the plan): it only describes things and never changes a case or a rating.
export function AiAnalyst({ ai, className = "" }: { ai: AiAnswer; className?: string }) {
  return (
    <Card className={`gap-3 ${className}`}>
      <div className="flex items-start gap-3">
        <span className="flex size-[2.4rem] flex-none items-center justify-center rounded-xl bg-crimson text-white">
          <Icon name="sparkle" size={19} />
        </span>
        <div className="flex-1">
          <h3 className="text-[1.06rem] font-extrabold tracking-[-0.015em]">AI analyst</h3>
          <p className={muted}>Ask about patterns across all complaints</p>
        </div>
        <Chip>Optional</Chip>
      </div>

      <div className="flex gap-2">
        <label className="sr-only" htmlFor="ai-question">
          Ask the AI analyst
        </label>
        <input id="ai-question" className={inputClass} defaultValue={ai.question} />
        <PillButton primary className="!h-11">
          Ask
        </PillButton>
      </div>

      <div className="flex flex-col gap-2.5 rounded-[1.25rem] border-[1.5px] border-[#efc9d1] bg-[#fbf0f2] px-4 py-3.5">
        <p className="text-[0.81rem] leading-[1.55]">{ai.answer}</p>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className={eyebrow}>Based on</span>
          {ai.basedOn.map((source) => (
            <Chip key={source} tone="brand">
              {source}
            </Chip>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {ai.suggestions.map((question) => (
          <PillButton key={question}>{question}</PillButton>
        ))}
      </div>
      <p className={`${muted} mt-auto`}>Summaries are advisory. They never change a case or a rating.</p>
    </Card>
  );
}
