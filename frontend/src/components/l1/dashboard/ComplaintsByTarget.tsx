import Link from "next/link";
import { Card, CardHeading, bigNumber } from "@/components/dashboard/ui";
import type { DashboardSummary, TargetFilter } from "./types";

const TARGETS: { code: Exclude<TargetFilter, "unclassified">; label: string }[] = [
  { code: "driver", label: "Driver" },
  { code: "conductor", label: "Conductor" },
  { code: "owner", label: "Owner" },
  { code: "bus_service", label: "Bus / Service" },
  { code: "other", label: "Other" },
];

// This officer's own complaints counted by who they are against. Each card opens My Complaints with that filter.
export function ComplaintsByTarget({
  counts,
  className = "",
}: {
  counts: DashboardSummary["byTarget"] | undefined;
  className?: string;
}) {
  const unclassified = counts?.unclassified ?? 0;
  return (
    <Card className={className}>
      <CardHeading
        title="Complaints by target"
        subtitle={
          counts
            ? unclassified > 0
              ? `Your complaints, by who they are against · ${unclassified} not classified yet`
              : "Your complaints, by who they are against"
            : "Loading…"
        }
      />
      <ul className="m-0 grid list-none grid-cols-2 gap-2.5 p-0 sm:grid-cols-3 min-[1200px]:grid-cols-5">
        {TARGETS.map((t) => (
          <li key={t.code}>
            <Link
              href={`/l1/complaints?target=${t.code}`}
              className="focus-ring flex flex-col gap-0.5 rounded-[1.25rem] bg-[#faf6f7] px-4 py-3 transition-shadow hover:shadow-[0_0_0_1.5px_rgba(179,17,47,0.35)]"
            >
              <span className="text-[0.75rem] font-bold text-muted">{t.label}</span>
              <span className={`${bigNumber} text-[1.7rem]`}>{counts ? counts[t.code] : "–"}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}
