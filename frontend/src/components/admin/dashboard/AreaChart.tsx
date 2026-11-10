import { useId } from "react";

// A line chart with a soft fill, drawn from a list of numbers.
// It takes its colour from the text colour of the element that sets its size,
// for example className="h-[10rem] text-crimson".

const WIDTH = 600;
const HEIGHT = 100;
const PADDING = 10;

function plot(values: number[]) {
  const min = Math.min(...values);
  const range = Math.max(...values) - min || 1;
  return values.map((value, i) => ({
    x: (i / (values.length - 1)) * WIDTH,
    y: PADDING + (1 - (value - min) / range) * (HEIGHT - 2 * PADDING),
  }));
}

export function AreaChart({
  values,
  label,
  markers = [],
  className = "",
}: {
  values: number[];
  label: string;
  markers?: number[]; // indexes of values to highlight with a dot
  className?: string;
}) {
  const gradientId = useId();
  const points = plot(values);
  const line = points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");

  return (
    <div className={`relative ${className}`}>
      <svg
        role="img"
        aria-label={label}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="none"
        className="absolute inset-0 size-full overflow-visible"
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="currentColor" stopOpacity="0.28" />
            <stop offset="1" stopColor="currentColor" stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={`${line} ${WIDTH},${HEIGHT} 0,${HEIGHT}`} fill={`url(#${gradientId})`} />
        <polyline
          points={line}
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      {markers.map((i) => (
        <span
          key={i}
          aria-hidden="true"
          className="absolute size-[0.8rem] -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-current bg-white"
          style={{ left: `${(points[i].x / WIDTH) * 100}%`, top: `${points[i].y}%` }}
        />
      ))}
    </div>
  );
}
