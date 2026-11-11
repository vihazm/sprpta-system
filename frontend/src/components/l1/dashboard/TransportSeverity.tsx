import { BarRows } from "@/components/dashboard/BarRows";
import { Donut } from "@/components/dashboard/Donut";
import { SEVERITY_COLOR, SEVERITY_LABEL } from "@/components/dashboard/severity";
import { Card, CardHeading, eyebrow } from "@/components/dashboard/ui";
import type { L1DashboardData } from "./types";

export function TransportSeverity({
  transport,
  severity,
  className = "",
}: {
  transport: L1DashboardData["transport"];
  severity: L1DashboardData["severity"];
  className?: string;
}) {
  const busiest = Math.max(...severity.map((s) => s.count));

  return (
    <Card className={className}>
      <CardHeading title="Transport and severity" subtitle="What you entered this month" />
      <Donut
        centerLabel="entered"
        segments={[
          { label: "Bus", value: transport.bus, color: "#b3112f" },
          { label: "Trishaw", value: transport.trishaw, color: "#f0b8c4" },
        ]}
      />
      <p className={eyebrow}>By severity</p>
      <BarRows
        labelWidth="4rem"
        items={severity.map((s) => ({
          label: SEVERITY_LABEL[s.severity],
          value: s.count,
          share: (s.count / busiest) * 100,
          color: SEVERITY_COLOR[s.severity],
        }))}
      />
    </Card>
  );
}
