import { bigNumber } from "@/components/dashboard/ui";
import { formatDuration, formatShortDay } from "./format";
import type { Uptime } from "./types";

const DAY_STYLE: Record<Uptime["days"][number], string> = {
  up: "h-full bg-white/85",
  down: "h-[55%] bg-amber-300",
  unknown: "h-[35%] bg-white/20",
};

export function UptimeTile({ uptime, className = "" }: { uptime: Uptime; className?: string }) {
  const { percent, days, trackingSince, lastOutage } = uptime;
  const outageDays = days.filter((day) => day === "down").length;

  return (
    <section
      className={`flex min-w-0 flex-col justify-between gap-4 rounded-[1.75rem] bg-slate-ink p-6 text-white shadow-[0_26px_50px_-34px_rgba(20,28,40,0.7)] ${className}`}
    >
      <div>
        <p className="text-[0.69rem] font-bold uppercase tracking-[0.09em] text-white/65">
          Uptime, 30 days
        </p>
        <p className={`${bigNumber} mt-2.5 text-[4.1rem]`}>
          {percent === null ? "–" : percent}
          {percent !== null && <span className="text-[1.9rem]">%</span>}
        </p>
      </div>

      <div
        role="img"
        aria-label={`Daily uptime for the last ${days.length} days, ${outageDays} with an outage`}
        className="grid h-[2.9rem] grid-cols-[repeat(30,minmax(0,1fr))] items-end gap-[0.2rem]"
      >
        {days.map((day, i) => (
          <div key={i} className={`rounded-[0.2rem] ${DAY_STYLE[day]}`} />
        ))}
      </div>

      <div className="border-t border-white/15 pt-3">
        {lastOutage ? (
          <>
            <p className="text-[0.81rem] font-bold">
              Last outage: {formatShortDay(lastOutage.startedAt)},{" "}
              {lastOutage.minutes === null ? "still going" : formatDuration(lastOutage.minutes)}
            </p>
            <p className="mt-0.5 text-[0.78rem] text-white/70">
              {lastOutage.serviceName}
              {lastOutage.reason && `: ${lastOutage.reason.toLowerCase()}`}
            </p>
          </>
        ) : (
          <>
            <p className="text-[0.81rem] font-bold">No outage recorded</p>
            <p className="mt-0.5 text-[0.78rem] text-white/70">
              {trackingSince
                ? `Checks began on ${formatShortDay(trackingSince)}.`
                : "Waiting for the first check."}
            </p>
          </>
        )}
      </div>
    </section>
  );
}
