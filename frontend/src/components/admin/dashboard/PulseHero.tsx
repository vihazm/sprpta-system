import { AreaChart } from "./AreaChart";
import type { Service, Tone } from "./types";

const RING_COLORS: Record<Tone, string> = {
  ok: "#ffffff",
  warn: "#ffc15a",
  crit: "#ff8a80",
  info: "#ffffff",
};

const PILL_DOTS: Record<Tone, string> = {
  ok: "bg-emerald-300",
  warn: "bg-amber-300",
  crit: "bg-red-300",
  info: "bg-slate-300",
};

const RING_GAP_DEGREES = 8;

// One arc per service, white when healthy and coloured when it is not.
function ringBackground(services: Service[]) {
  const arc = 360 / services.length;
  const parts = services.map((service, i) => {
    const start = i * arc;
    const end = start + arc - RING_GAP_DEGREES;
    return `${RING_COLORS[service.tone]} ${start}deg ${end}deg, transparent ${end}deg ${start + arc}deg`;
  });
  return `conic-gradient(from -90deg, ${parts.join(", ")})`;
}

const RING_HOLE = "radial-gradient(farthest-side, transparent calc(100% - 0.95rem), #000 calc(100% - 0.9rem))";

export function PulseHero({
  services,
  apiResponseMs,
  lastBackup,
  className = "",
}: {
  services: Service[];
  apiResponseMs: number[];
  lastBackup?: { when: string; succeeded: boolean }; // left out until backups are recorded
  className?: string;
}) {
  const healthy = services.filter((s) => s.tone === "ok").length;
  const problem = services.find((s) => s.tone !== "ok");
  const headline = services.some((s) => s.tone === "crit")
    ? "Needs attention"
    : problem
      ? "One thing to watch"
      : "Running smoothly";

  return (
    <section
      className={`relative flex flex-col justify-between gap-5 overflow-hidden rounded-[2rem] bg-gradient-to-br from-crimson-deep via-[#A8102F] to-[#cf2a4b] px-8 pt-[1.9rem] text-white shadow-[0_34px_60px_-36px_rgba(110,8,30,0.75)] ${className}`}
    >
      <div
        aria-hidden="true"
        className="absolute -right-24 -top-28 size-[24rem] rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.2),transparent_65%)]"
      />

      <div className="relative flex flex-wrap items-center justify-between gap-6">
        <div className="min-w-[16rem] flex-1">
          <p className="text-[0.69rem] font-bold uppercase tracking-[0.1em] text-white/75">
            System pulse
          </p>
          <h3 className="mt-2 font-display text-[3rem] leading-[1.02] tracking-[-0.035em]">
            {headline}
          </h3>
          <p className="mt-3 max-w-[24rem] text-[0.94rem] leading-[1.5] text-white/90">
            {healthy} of {services.length} services are healthy.{" "}
            {problem
              ? `The ${problem.name} is ${problem.detail} right now.`
              : "Everything is responding normally."}
          </p>
        </div>

        <div className="relative size-[9.75rem] flex-none">
          <div
            className="absolute inset-0 rounded-full"
            style={{ background: ringBackground(services), WebkitMask: RING_HOLE, mask: RING_HOLE }}
          />
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-display text-[2.5rem] leading-none tabular-nums">
              {healthy}/{services.length}
            </span>
            <span className="mt-0.5 text-[0.69rem] font-bold uppercase tracking-[0.08em] text-white/75">
              healthy
            </span>
          </div>
        </div>
      </div>

      <ul className="relative flex list-none flex-wrap gap-2 p-0">
        {services.map((service) => (
          <li
            key={service.name}
            className="inline-flex items-center gap-2 whitespace-nowrap rounded-full border border-white/25 bg-white/15 px-[0.8rem] py-[0.45rem] text-[0.78rem] font-semibold backdrop-blur-sm"
          >
            <span aria-hidden="true" className={`size-2 rounded-full ${PILL_DOTS[service.tone]}`} />
            {service.name}
            <span className="font-medium text-white/75">{service.detail}</span>
          </li>
        ))}
      </ul>

      <div className="relative -mx-8">
        <div className="absolute left-8 top-1.5 z-10 flex flex-wrap gap-[0.6rem] text-[0.75rem] font-semibold">
          <span className="rounded-full border border-white/25 bg-white/15 px-[0.7rem] py-[0.3rem] backdrop-blur-sm">
            API response time, 24 hours
          </span>
          {lastBackup && (
            <span className="inline-flex items-center gap-[0.4rem] rounded-full border border-white/25 bg-white/15 px-[0.7rem] py-[0.3rem] backdrop-blur-sm">
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                className="text-emerald-300"
              >
                <path d="M5 12.5l4.5 4.5L19 7.5" />
              </svg>
              Last backup {lastBackup.when}, {lastBackup.succeeded ? "successful" : "failed"}
            </span>
          )}
        </div>
        {apiResponseMs.length > 1 ? (
          <AreaChart
            values={apiResponseMs}
            label="API response time over the last 24 hours"
            className="h-[5.25rem] text-white"
          />
        ) : (
          <p className="flex h-[5.25rem] items-end px-8 pb-3 text-[0.78rem] text-white/70">
            Collecting API response times…
          </p>
        )}
      </div>
    </section>
  );
}
