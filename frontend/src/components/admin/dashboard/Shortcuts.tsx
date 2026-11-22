import type { AdminDashboardData } from "./types";
import { PillButton, PillLink, eyebrow } from "@/components/dashboard/ui";

export function Shortcuts({
  timeTargets,
  className = "",
}: {
  timeTargets: AdminDashboardData["timeTargets"];
  className?: string;
}) {
  return (
    <section className={`flex min-w-0 flex-col gap-4 rounded-[1.75rem] bg-crimson/10 p-6 ${className}`}>
      <h3 className="text-[1.06rem] font-extrabold tracking-[-0.015em] text-crimson-deep">Shortcuts</h3>

      <div className="grid grid-cols-2 gap-2">
        <PillLink href="/admin/users" primary className="h-10">
          Create user
        </PillLink>
        <PillLink href="/admin/master-data/vehicles" className="h-10">
          Add vehicle
        </PillLink>
        <PillButton className="h-10">Upload policy</PillButton>
        <PillButton className="h-10">Edit template</PillButton>
      </div>

      <div className="flex flex-col gap-[0.6rem] border-t border-crimson/20 pt-4">
        <p className={`${eyebrow} text-crimson-hover`}>Time targets in force, days</p>
        {timeTargets.map((t) => (
          <div key={t.severity} className="flex items-center justify-between gap-2">
            <span className="text-[0.8rem] font-bold">{t.severity}</span>
            <span className="text-[0.78rem] tabular-nums text-crimson-deep">
              forward {t.forwardDays === 0 ? "same day" : t.forwardDays}, decide {t.decideDays}, close{" "}
              {t.closeDays}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
