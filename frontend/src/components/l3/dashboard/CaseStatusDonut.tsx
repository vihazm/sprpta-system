import { Donut, type Segment } from "@/components/dashboard/Donut";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading } from "@/components/dashboard/ui";

export function CaseStatusDonut({
  statuses,
  overdue,
  overdueAtLevel2,
  className = "",
}: {
  statuses: Segment[];
  overdue: number;
  overdueAtLevel2: number;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeading title="Where cases stand" subtitle="This month" />
      <Donut segments={statuses} centerLabel="cases" size="8.5rem" />
      <Note tone="alert" className="mt-auto">
        <b className="font-extrabold">{overdue} cases</b> are past their time target. This is an alert only, nothing
        happens automatically. {overdueAtLevel2} sit at Level 2.
      </Note>
    </Card>
  );
}
