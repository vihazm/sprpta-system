import { ChoiceGroup } from "@/components/dashboard/ChoiceGroup";
import { inputClass } from "@/components/dashboard/controls";
import { Card, CardHeading, PillButton } from "@/components/dashboard/ui";
import type { L1DashboardData } from "./types";

const KINDS = ["Vehicle", "Permit", "Person"].map((value) => ({ value }));

// Look a record up before entering a complaint (UC-L1-02). Not wired up yet: there is no master data.
export function QuickLookup({
  lookup,
  className = "",
}: {
  lookup: L1DashboardData["lookup"];
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeading title="Quick lookup" subtitle="Check the records before you enter a complaint" />
      <ChoiceGroup label="Look up a" choices={KINDS} defaultValue="Vehicle" look="dark" />
      <div className="flex gap-2">
        <label className="sr-only" htmlFor="lookup-query">
          Number to look up
        </label>
        <input id="lookup-query" className={inputClass} defaultValue={lookup.query} />
        <PillButton primary className="!h-11">
          Go
        </PillButton>
      </div>
      <dl className="m-0 flex flex-col gap-1.5">
        {lookup.rows.map((row) => (
          <div key={row.label} className="flex justify-between gap-3 rounded-xl bg-[#f7f4f5] px-3 py-2.5 text-[0.78rem]">
            <dt className="text-muted">{row.label}</dt>
            <dd className="m-0 font-extrabold">{row.value}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
