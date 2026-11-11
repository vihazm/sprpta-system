import { ChoiceGroup } from "@/components/dashboard/ChoiceGroup";
import { Field, inputClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { Card, CardHeading, PillButton } from "@/components/dashboard/ui";

const REPORT_TYPES = [
  "Summary",
  "By area",
  "By transport mode",
  "Staff ratings",
  "Rejection reasons",
  "Time targets",
].map((value) => ({ value }));

// Build a report for a period and export it (UC-L3-04). Not wired up yet: there is nothing to report on.
export function ReportGenerator({ className = "" }: { className?: string }) {
  return (
    <Card className={className}>
      <CardHeading title="Report generator" subtitle="Build a report for any period" />
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Period" htmlFor="report-period">
          <select id="report-period" className={inputClass}>
            <option>Last quarter (Jul to Sep 2026)</option>
            <option>This month</option>
            <option>Last 12 months</option>
          </select>
        </Field>
        <Field label="Area" htmlFor="report-area">
          <select id="report-area" className={inputClass}>
            <option>All areas</option>
            <option>Galle</option>
            <option>Matara</option>
            <option>Hambantota</option>
          </select>
        </Field>
      </div>
      <Field label="Report type">
        <ChoiceGroup
          label="Report type"
          choices={REPORT_TYPES}
          defaultValue={["Summary", "Staff ratings"]}
          multiple
        />
      </Field>
      <div className="mt-auto flex flex-wrap gap-2.5">
        <PillButton primary>View report</PillButton>
        <PillButton className="!border-ink !bg-ink !text-white hover:!border-crimson">
          <Icon name="download" size={14} />
          Export PDF
        </PillButton>
        <PillButton>
          <Icon name="download" size={14} />
          Export Excel
        </PillButton>
      </div>
    </Card>
  );
}
