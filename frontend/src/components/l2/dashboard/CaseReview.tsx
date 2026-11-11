import { Icon } from "@/components/dashboard/icons";
import { SeverityChip } from "@/components/dashboard/severity";
import { Card, Chip, muted } from "@/components/dashboard/ui";
import { AiSuggestion } from "./AiSuggestion";
import { DecisionForm } from "./DecisionForm";
import type { ReviewedCase } from "./types";

const OUTCOME_TONE: Record<string, "warn" | "brand" | "info"> = { Warning: "warn", Fine: "brand" };

// The case the officer is working on: its details, the AI's advice and the decision form.
export function CaseReview({ review, className = "" }: { review: ReviewedCase; className?: string }) {
  return (
    <Card className={`gap-4 ${className}`}>
      <div className="flex flex-wrap items-start justify-between gap-3.5">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <h3 className="font-display text-[1.6rem] leading-[1.1] tracking-[-0.035em]">{review.ref}</h3>
            <SeverityChip severity={review.severity} />
            <Chip>Under review</Chip>
          </div>
          <p className={`mt-1 ${muted}`}>
            {review.title} · forwarded by {review.forwardedBy} {review.forwardedAgo}
          </p>
        </div>
        <div className="rounded-2xl bg-crimson/10 px-3.5 py-2 text-right">
          <p className="text-[0.78rem] font-extrabold text-crimson-deep">Decide within {review.decideWithin}</p>
          <p className="text-[0.75rem] text-crimson-hover">Due in {review.dueIn}</p>
        </div>
      </div>

      <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-3 rounded-[1.25rem] bg-[#f7f4f5] p-4 sm:grid-cols-4">
        {review.facts.map((fact) => (
          <div key={fact.label}>
            <dt className="text-[0.69rem] font-bold text-muted">{fact.label}</dt>
            <dd className={`m-0 mt-0.5 text-[0.81rem] font-extrabold ${fact.accent ? "text-crimson-hover" : ""}`}>
              {fact.value}
            </dd>
          </div>
        ))}
      </dl>

      <div>
        <p className="text-[0.84rem] leading-[1.55]">
          <b className="font-extrabold">What happened.</b> {review.story}
        </p>
        <div className="mt-2.5 flex flex-wrap gap-2">
          {review.attachments.map((file) => (
            <span
              key={file}
              className="inline-flex items-center gap-1.5 rounded-[0.65rem] border border-[#ecd2d8] px-2.5 py-1 text-[0.75rem] font-bold text-slate-600"
            >
              <Icon name="attach" size={13} />
              {file}
            </span>
          ))}
        </div>
      </div>

      <AiSuggestion ai={review.ai} />
      <DecisionForm />

      <p className="text-[0.69rem] font-bold uppercase tracking-[0.09em] text-muted">
        Earlier cases for this vehicle or person
      </p>
      <ul className="m-0 flex list-none flex-col p-0">
        {review.earlier.map((e) => (
          <li key={e.ref} className="flex items-center gap-3 border-t border-[#f1ebed] py-2.5 first:border-t-0 first:pt-0">
            <b className="w-[6.5rem] text-[0.75rem] font-extrabold text-crimson-hover">{e.ref}</b>
            <span className="min-w-0 flex-1 truncate text-[0.81rem] font-semibold">{e.title}</span>
            <Chip tone={OUTCOME_TONE[e.outcome] ?? "info"}>{e.outcome}</Chip>
            <span className={`${muted} w-[3.9rem] text-right`}>{e.when}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
