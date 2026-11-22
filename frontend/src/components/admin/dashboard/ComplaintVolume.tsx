import { AreaChart } from "./AreaChart";
import { sum } from "./format";
import type { AdminDashboardData } from "./types";
import { Card, CardHeading, Chip, LinkButton, bigNumber, muted } from "@/components/dashboard/ui";

// Colours for the status bar, in the order the statuses are listed.
const STATUS_COLORS = [
  "bg-slate-400",
  "bg-crimson",
  "bg-rose-400",
  "bg-rose-200",
  "bg-slate-200",
  "bg-slate-800",
  "bg-red-900",
];

export function ComplaintVolume({
  complaints,
  className = "",
}: {
  complaints: AdminDashboardData["complaints"];
  className?: string;
}) {
  const total = sum(complaints.byStatus);
  const mostComplaints = Math.max(1, ...complaints.byArea.map((a) => a.count));

  // "54 closed, 21 forwarded, 17 under review, 26 in other steps", largest first
  const biggest = [...complaints.byStatus].sort((a, b) => b.count - a.count);
  const others = sum(biggest.slice(3));
  const caption = [
    ...biggest.slice(0, 3).map((s) => `${s.count} ${s.label.toLowerCase()}`),
    ...(others > 0 ? [`${others} in other steps`] : []),
  ].join(", ");

  return (
    <Card className={className}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <CardHeading title="Complaints, last 30 days" subtitle="Counts only, personal data masked" />
        <div className="flex items-center gap-[0.4rem]">
          <Chip tone={complaints.overdue > 0 ? "warn" : "ok"}>{complaints.overdue} overdue now</Chip>
          <LinkButton href="/admin/statistics">Statistics</LinkButton>
        </div>
      </div>

      {total === 0 ? (
        <p className={muted}>No complaint has been registered in the last 30 days.</p>
      ) : (
        <div className="flex flex-wrap items-stretch gap-[1.4rem]">
          <div className="min-w-[16rem] flex-[2_1_21rem]">
            <div className="flex items-baseline gap-[0.6rem]">
              <p className={`${bigNumber} text-[3.5rem]`}>{total}</p>
              <p className={muted}>registered, last 30 days</p>
            </div>
            <AreaChart
              values={complaints.perDay}
              label="Complaints registered per day over the last 30 days"
              className="mt-2 h-[7.5rem] text-crimson"
            />
          </div>

          <div className="flex min-w-[13rem] flex-[1_1_13.5rem] flex-col gap-3">
            <ul className="grid list-none grid-cols-3 gap-2 p-0">
              {complaints.byArea.map((area) => (
                <li key={area.label} className="rounded-[1.1rem] bg-crimson/5 px-3 pb-[0.65rem] pt-3">
                  <p className={`${bigNumber} text-[1.9rem]`}>{area.count}</p>
                  <p className="mt-1 text-[0.72rem] font-bold">{area.label}</p>
                  <div className="mt-2 h-[0.3rem] rounded-full bg-white">
                    <div
                      className="h-full rounded-full bg-crimson"
                      style={{ width: `${(area.count / mostComplaints) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>

            <div>
              <div className="flex h-3 gap-0.5 overflow-hidden rounded-full">
                {complaints.byStatus.map((status, i) => (
                  <div
                    key={status.label}
                    className={STATUS_COLORS[i % STATUS_COLORS.length]}
                    style={{ width: `${(status.count / total) * 100}%` }}
                  />
                ))}
              </div>
              <p className={`mt-[0.4rem] ${muted}`}>By status: {caption}.</p>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
