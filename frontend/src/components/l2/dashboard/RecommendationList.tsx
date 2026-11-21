import Link from "next/link";
import { Icon } from "@/components/dashboard/icons";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, Chip, LinkButton, muted } from "@/components/dashboard/ui";
import { RECOMMENDATION_STATUS_LABEL, RECOMMENDATION_TONE, RECOMMENDATION_TYPE_LABEL, shortDate } from "../format";
import type { RecommendationRow } from "../types";

// The newest recommendations, read-only: only Level 3 changes a recommendation's status.
export function RecommendationList({ items, className = "" }: { items: RecommendationRow[]; className?: string }) {
  return (
    <Card className={className}>
      <CardHeading
        title="Recommendations"
        subtitle="Entered by Level 1 · you can read them, Level 3 manages them"
        action={<LinkButton href="/l2/recommendations">See all</LinkButton>}
      />
      {items.length === 0 && <Note>No recommendations have been entered yet.</Note>}
      <ul className="m-0 flex list-none flex-col p-0">
        {items.map((item) => (
          <li key={item.id} className="border-t border-[#f1ebed] first:border-t-0">
            <Link
              href={`/l2/recommendations/${item.id}`}
              className="focus-ring -mx-2 flex items-center gap-3 rounded-xl px-2 py-2.5 hover:bg-[#f7f4f5]"
            >
              <span className="flex size-9 flex-none items-center justify-center rounded-xl bg-crimson/10 text-crimson-hover">
                <Icon name="bulb" size={17} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[0.81rem] font-extrabold">{item.title}</span>
                <span className={muted}>
                  {RECOMMENDATION_TYPE_LABEL[item.type]} · {shortDate(item.createdAt)}
                </span>
              </span>
              <Chip tone={RECOMMENDATION_TONE[item.status]}>{RECOMMENDATION_STATUS_LABEL[item.status]}</Chip>
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}
