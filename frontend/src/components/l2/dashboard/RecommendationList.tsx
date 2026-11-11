import { Icon } from "@/components/dashboard/icons";
import { Card, CardHeading, Chip, LinkButton, muted } from "@/components/dashboard/ui";
import type { RecommendationItem } from "./types";

const STATUS_TONE: Record<string, "info" | "ok" | "warn" | "brand"> = {
  New: "info",
  Acknowledged: "ok",
  "Under consideration": "warn",
  "Commendation verified": "brand",
};

// The recommendation register, read-only: only Level 3 changes a recommendation's status.
export function RecommendationList({
  items,
  className = "",
}: {
  items: RecommendationItem[];
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeading
        title="Recommendations"
        subtitle="Entered by Level 1 · you can read them, Level 3 manages them"
        action={<LinkButton>See all</LinkButton>}
      />
      <ul className="m-0 flex list-none flex-col p-0">
        {items.map((item) => (
          <li key={item.ref} className="flex items-center gap-3 border-t border-[#f1ebed] py-2.5 first:border-t-0 first:pt-0">
            <span className="flex size-9 flex-none items-center justify-center rounded-xl bg-crimson/10 text-crimson-hover">
              <Icon name="bulb" size={17} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[0.81rem] font-extrabold">{item.title}</p>
              <p className={muted}>
                {item.ref} · {item.kind}
              </p>
            </div>
            <Chip tone={STATUS_TONE[item.status] ?? "info"}>{item.status}</Chip>
          </li>
        ))}
      </ul>
    </Card>
  );
}
