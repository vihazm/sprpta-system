import { Card, Chip, StatusDot, muted } from "@/components/dashboard/ui";
import type { UsersSummary } from "./types";

// What the two boxes shrink to while the form is open, so coverage stays in sight.
export function CoverageStrip({ summary }: { summary: UsersSummary }) {
  return (
    <Card className="flex-row flex-wrap items-center gap-x-3.5 gap-y-2 !bg-crimson/10 !px-[1.1rem] !py-3.5 !shadow-none">
      {summary.areas.map((area) => {
        const tone = area.officerName ? "ok" : "crit";
        return (
          <Chip key={area.id} tone={tone}>
            <StatusDot tone={tone} />
            {area.name}
          </Chip>
        );
      })}
      <span className={`ml-auto ${muted}`}>
        {summary.locked} locked · {summary.inactive} deactivated
      </span>
    </Card>
  );
}
