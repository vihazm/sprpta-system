import type { Choice } from "./ChoiceGroup";

export type Severity = "critical" | "high" | "medium" | "low";

export const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

const CHIP_STYLE: Record<Severity, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-sky-100 text-sky-800",
};

// The same four colours are used for severity dots and bars everywhere.
export const SEVERITY_COLOR: Record<Severity, string> = {
  critical: "#a8190e",
  high: "#d9680b",
  medium: "#d9a30b",
  low: "#2e7bc4",
};

export const SEVERITY_CHOICES: Choice[] = (Object.keys(SEVERITY_LABEL) as Severity[]).map((s) => ({
  value: SEVERITY_LABEL[s],
  dot: SEVERITY_COLOR[s],
}));

export function SeverityChip({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex whitespace-nowrap rounded-full px-[0.6rem] py-[0.15rem] text-[0.69rem] font-bold ${CHIP_STYLE[severity]}`}
    >
      {SEVERITY_LABEL[severity]}
    </span>
  );
}
