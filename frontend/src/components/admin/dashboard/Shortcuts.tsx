import type { AdminDashboardData } from "./types";
import { PillButton, eyebrow } from "@/components/dashboard/ui";

export function Shortcuts({
  timeTargets,
  settings,
  className = "",
}: {
  timeTargets: AdminDashboardData["timeTargets"];
  settings: AdminDashboardData["settings"];
  className?: string;
}) {
  return (
    <section className={`flex min-w-0 flex-col gap-4 rounded-[1.75rem] bg-crimson/10 p-6 ${className}`}>
      <h3 className="text-[1.06rem] font-extrabold tracking-[-0.015em] text-crimson-deep">Shortcuts</h3>

      <div className="grid grid-cols-2 gap-2">
        <PillButton primary className="h-10">Create user</PillButton>
        <PillButton className="h-10">Add vehicle</PillButton>
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
        <div className="mt-0.5 flex flex-wrap gap-[0.4rem] text-[0.72rem] font-bold text-crimson-deep">
          <span className="rounded-full bg-white px-[0.7rem] py-1">
            Rating formula v{settings.ratingFormulaVersion}
          </span>
          <span className="rounded-full bg-white px-[0.7rem] py-1">
            AI timeout {settings.aiTimeoutSeconds} s
          </span>
        </div>
      </div>
    </section>
  );
}
