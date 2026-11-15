import { BarRows } from "@/components/dashboard/BarRows";
import { Donut } from "@/components/dashboard/Donut";
import { SEVERITY_COLOR, SEVERITY_LABEL } from "@/components/dashboard/severity";
import { Card, CardHeading, eyebrow, muted } from "@/components/dashboard/ui";
import type { DashboardOverview } from "./types";

// What this officer entered this month: bus or trishaw, and how serious.
export function TransportSeverity({
  transport,
  severity,
  className = "",
}: {
  transport: DashboardOverview["transport"] | undefined;
  severity: DashboardOverview["severity"] | undefined;
  className?: string;
}) {
  const entered = transport ? transport.bus + transport.trishaw + transport.unknown : 0;
  const busiest = Math.max(1, ...(severity ?? []).map((s) => s.count));

  return (
    <Card className={className}>
      <CardHeading title="Transport and severity" subtitle={transport ? "What you entered this month" : "Loading…"} />
      {transport && entered === 0 ? (
        <p className={muted}>You have not entered a complaint this month yet.</p>
      ) : (
        transport && (
          <Donut
            centerLabel="entered"
            segments={[
              { label: "Bus", value: transport.bus, color: "#b3112f" },
              { label: "Trishaw", value: transport.trishaw, color: "#f0b8c4" },
              ...(transport.unknown > 0 ? [{ label: "No vehicle yet", value: transport.unknown, color: "#d9d2d5" }] : []),
            ]}
          />
        )
      )}
      <p className={eyebrow}>By severity</p>
      <BarRows
        labelWidth="4rem"
        items={(severity ?? []).map((s) => ({
          label: SEVERITY_LABEL[s.severity],
          value: s.count,
          share: (s.count / busiest) * 100,
          color: SEVERITY_COLOR[s.severity],
        }))}
      />
    </Card>
  );
}
