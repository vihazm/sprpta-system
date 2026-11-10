import type { ReactNode } from "react";
import type { Tone } from "./types";

// Small building blocks shared by the dashboard tiles.

type ChipTone = Tone | "brand";

const CHIP_STYLES: Record<ChipTone, string> = {
  ok: "bg-emerald-50 text-emerald-800",
  warn: "bg-amber-50 text-amber-900",
  crit: "bg-red-50 text-red-800",
  info: "bg-slate-100 text-slate-700",
  brand: "bg-crimson/10 text-crimson-hover",
};

export const TONE_BG: Record<Tone, string> = {
  ok: "bg-emerald-500",
  warn: "bg-amber-500",
  crit: "bg-red-500",
  info: "bg-slate-400",
};

export const eyebrow = "text-[0.69rem] font-bold uppercase tracking-[0.09em] text-muted";
export const muted = "text-[0.78rem] leading-[1.45] text-muted";
export const bigNumber = "font-display leading-none tracking-[-0.035em] tabular-nums";

export function Chip({ tone = "info", children }: { tone?: ChipTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-[0.35rem] whitespace-nowrap rounded-full px-[0.7rem] py-[0.25rem] text-[0.72rem] font-bold ${CHIP_STYLES[tone]}`}
    >
      {children}
    </span>
  );
}

export function StatusDot({ tone }: { tone: Tone }) {
  return <span aria-hidden="true" className={`size-[0.55rem] flex-none rounded-full ${TONE_BG[tone]}`} />;
}

export function Card({ className = "", children }: { className?: string; children: ReactNode }) {
  return (
    <section
      className={`flex min-w-0 flex-col gap-4 rounded-[1.75rem] bg-white p-6 shadow-[0_1px_2px_rgba(60,20,30,0.05),0_22px_44px_-30px_rgba(110,8,30,0.28),0_0_0_1px_rgba(60,20,30,0.03)] ${className}`}
    >
      {children}
    </section>
  );
}

export function CardHeading({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div>
        <h3 className="text-[1.06rem] font-extrabold tracking-[-0.015em]">{title}</h3>
        {subtitle && <p className={`mt-0.5 ${muted}`}>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

// These buttons are not wired up yet: the screens they open are still to be built.
export function PillButton({
  children,
  primary = false,
  className = "",
}: {
  children: ReactNode;
  primary?: boolean;
  className?: string;
}) {
  const look = primary
    ? "border-crimson bg-crimson text-white hover:bg-crimson-hover"
    : "border-[#E5E7EB] bg-white text-slate-ink hover:border-crimson hover:text-crimson";
  return (
    <button
      type="button"
      className={`focus-ring inline-flex h-[2.1rem] cursor-pointer items-center justify-center gap-[0.45rem] whitespace-nowrap rounded-full border-[1.5px] px-[0.95rem] text-[0.78rem] font-bold transition-colors ${look} ${className}`}
    >
      {children}
    </button>
  );
}
