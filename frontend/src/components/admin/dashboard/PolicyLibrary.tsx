import { formatNumber, plural } from "./format";
import type { AdminDashboardData } from "./types";
import { Card, CardHeading, Chip, bigNumber, muted } from "@/components/dashboard/ui";

export function PolicyLibrary({
  policy,
  className = "",
}: {
  policy: AdminDashboardData["policy"];
  className?: string;
}) {
  return (
    <Card className={`gap-3 ${className}`}>
      <CardHeading title="Policy library" subtitle="What the AI can cite" />
      <div className="flex items-baseline gap-2">
        <p className={`${bigNumber} text-[3.25rem]`}>{policy.activeVersions}</p>
        <p className={muted}>active versions</p>
      </div>
      <p className="text-[0.8rem] font-semibold">{formatNumber(policy.clauses)} clauses searchable</p>
      <div className="flex flex-col items-start gap-2">
        {policy.draftsWaiting > 0 && (
          <Chip>{plural(policy.draftsWaiting, "draft")} waiting for approval</Chip>
        )}
        {policy.failedScans > 0 && (
          <Chip tone="crit">{plural(policy.failedScans, "scan")} failed to index</Chip>
        )}
      </div>
      <p className={muted}>
        AI, 24 hours: {policy.aiRequests} requests, {policy.aiTimeouts} timed out.
      </p>
    </Card>
  );
}
