import { Icon } from "@/components/dashboard/icons";
import { Note } from "@/components/dashboard/Note";
import { Card, Chip, PillLink, muted } from "@/components/dashboard/ui";
import { dateTime, RECOMMENDATION_STATUS_LABEL, RECOMMENDATION_TONE, RECOMMENDATION_TYPE_LABEL, shortDate } from "../format";
import type { RecommendationDetail } from "../types";

// One recommendation and its status (UI-L2-10). There are no status controls: only Level 3 changes them.
export function RecommendationView({ r }: { r: RecommendationDetail }) {
  const facts = [
    { label: "Type", value: RECOMMENDATION_TYPE_LABEL[r.type] },
    { label: "Received", value: shortDate(r.receivedDate) },
    { label: "Medium", value: r.medium ?? "–" },
    { label: "Entered by", value: `${r.enteredBy} (Level 1)` },
    ...(r.person ? [{ label: "Person commended", value: r.person }] : []),
    { label: "Status changed", value: r.statusChangedAt ? dateTime(r.statusChangedAt) : "Not yet" },
  ];

  return (
    <Card className="max-w-[52rem]">
      <PillLink href="/l2/recommendations" className="self-start">
        <Icon name="prev" size={12} />
        All recommendations
      </PillLink>
      <div>
        <div className="flex flex-wrap items-center gap-2.5">
          <h2 className="font-display text-[1.6rem] leading-[1.15] tracking-[-0.035em]">{r.title}</h2>
          <Chip tone={RECOMMENDATION_TONE[r.status]}>{RECOMMENDATION_STATUS_LABEL[r.status]}</Chip>
        </div>
        <p className={`mt-1 ${muted}`}>Entered {dateTime(r.createdAt)}</p>
      </div>
      <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-3 rounded-[1.25rem] bg-[#f7f4f5] p-4 sm:grid-cols-3">
        {facts.map((f) => (
          <div key={f.label}>
            <dt className="text-[0.69rem] font-bold text-muted">{f.label}</dt>
            <dd className="m-0 mt-0.5 text-[0.81rem] font-extrabold">{f.value}</dd>
          </div>
        ))}
      </dl>
      <p className="whitespace-pre-line text-[0.88rem] leading-[1.6]">{r.details}</p>
      <Note>Read-only. Only Level 3 changes the status of a recommendation.</Note>
    </Card>
  );
}
