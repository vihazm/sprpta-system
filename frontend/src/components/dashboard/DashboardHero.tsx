import type { ReactNode } from "react";
import { Icon } from "./icons";

// The crimson banner at the top of the Level 1, 2 and 3 dashboards: a greeting, the main
// actions, and a small panel with the day's (or month's) three key figures.
export function DashboardHero({
  date,
  title,
  intro,
  actions,
  summaryTitle,
  tiles,
  summaryNote,
}: {
  date: string;
  title: string;
  intro: string;
  actions: ReactNode;
  summaryTitle: string;
  tiles: { value: string | number; label: string }[];
  summaryNote: string;
}) {
  return (
    <section className="relative flex flex-wrap justify-between gap-[1.6rem] overflow-hidden rounded-[2rem] bg-gradient-to-br from-crimson-deep via-[#A8102F] to-[#cf2a4b] p-[1.9rem] text-white shadow-[0_34px_60px_-36px_rgba(110,8,30,0.75)]">
      <div
        aria-hidden="true"
        className="absolute -right-24 -top-32 size-[25rem] rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.2),transparent_65%)]"
      />

      <div className="relative flex min-w-0 flex-[1_1_23rem] flex-col justify-between gap-5">
        <div>
          <p className="text-[0.75rem] font-semibold text-white/80">{date}</p>
          <h2 className="mt-2 font-display text-[2.75rem] leading-[1.05] tracking-[-0.035em]">{title}</h2>
          <p className="mt-2.5 max-w-[28rem] text-[0.88rem] leading-[1.5] text-white/90">{intro}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">{actions}</div>
      </div>

      <div className="relative flex min-w-[18rem] flex-[0_1_26rem] flex-col gap-3.5 rounded-[1.6rem] border border-white/25 bg-white/15 p-5">
        <p className="text-[0.69rem] font-bold uppercase tracking-[0.1em] text-white/80">{summaryTitle}</p>
        <div className="grid grid-cols-3 gap-2.5">
          {tiles.map((tile, i) => (
            <div key={tile.label} className={`rounded-[1.1rem] p-3.5 ${i < 2 ? "bg-white text-ink" : "bg-white/20"}`}>
              <p className="font-display text-[2.4rem] leading-none tracking-[-0.035em] tabular-nums">{tile.value}</p>
              <p className={`mt-1 text-[0.75rem] font-bold ${i < 2 ? "text-muted" : "text-white/85"}`}>{tile.label}</p>
            </div>
          ))}
        </div>
        <p className="text-[0.75rem] text-white/80">{summaryNote}</p>
      </div>
    </section>
  );
}

// A white button for the hero's main action, and a see-through one for the second.
export function HeroButton({ children, filled = false }: { children: ReactNode; filled?: boolean }) {
  return (
    <button
      type="button"
      className={`focus-ring inline-flex h-[2.6rem] cursor-pointer items-center gap-[0.45rem] whitespace-nowrap rounded-full border-[1.5px] px-5 text-[0.78rem] font-bold transition-colors ${
        filled
          ? "border-white bg-white text-crimson-hover hover:bg-white/90"
          : "border-white/60 text-white hover:bg-white/10"
      }`}
    >
      {children}
    </button>
  );
}

// Finds a case by its reference number. Not wired up yet: there are no cases to search.
export function ReferenceSearch() {
  return (
    <label className="flex h-[2.6rem] items-center gap-2 rounded-full border border-white/30 bg-white/15 px-4 text-white/90">
      <Icon name="search" size={15} />
      <span className="sr-only">Find a case by reference number</span>
      <input
        type="search"
        placeholder="Find reference no."
        className="w-[8.5rem] bg-transparent text-[0.8rem] text-white outline-none placeholder:text-white/80"
      />
    </label>
  );
}
