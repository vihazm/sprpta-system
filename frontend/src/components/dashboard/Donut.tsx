import { bigNumber, muted } from "./ui";

export type Segment = { label: string; value: number; color: string };

const HOLE = "radial-gradient(farthest-side, transparent calc(100% - 1.4rem), #000 calc(100% - 1.35rem))";

// A ring split into coloured segments, with the total in the middle and a legend beside it.
export function Donut({
  segments,
  centerLabel,
  size = "8.5rem",
}: {
  segments: Segment[];
  centerLabel: string;
  size?: string;
}) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  const percent = (amount: number) => (amount / total) * 100;
  const stops = segments.map((s, i) => {
    const before = segments.slice(0, i).reduce((sum, other) => sum + other.value, 0);
    return `${s.color} ${percent(before)}% ${percent(before + s.value)}%`;
  });

  return (
    <div className="flex flex-wrap items-center gap-[1.1rem]">
      <div className="relative flex-none" style={{ width: size, height: size }}>
        <div
          className="absolute inset-0 rounded-full"
          style={{ background: `conic-gradient(${stops.join(", ")})`, WebkitMask: HOLE, mask: HOLE }}
        />
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`${bigNumber} text-[2rem]`}>{total}</span>
          <span className={muted}>{centerLabel}</span>
        </div>
      </div>
      <ul className="m-0 flex min-w-[9rem] flex-1 list-none flex-col gap-[0.45rem] p-0">
        {segments.map((s) => (
          <li key={s.label} className="flex items-center gap-2.5 text-[0.78rem]">
            <span aria-hidden="true" className="size-[0.55rem] flex-none rounded-full" style={{ background: s.color }} />
            <span className="flex-1 font-bold">{s.label}</span>
            <b className="font-extrabold tabular-nums">{s.value}</b>
          </li>
        ))}
      </ul>
    </div>
  );
}
