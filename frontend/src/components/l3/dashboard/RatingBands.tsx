import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, Chip, bigNumber } from "@/components/dashboard/ui";
import { BAND_TILE, BAND_TONE } from "./bands";
import type { L3DashboardData } from "./types";

// How many rated people fall in each band.
export function RatingBands({
  bands,
  className = "",
}: {
  bands: L3DashboardData["bands"];
  className?: string;
}) {
  const rated = bands.reduce((sum, b) => sum + b.count, 0);
  const poor = bands.find((b) => b.band === "Poor")?.count ?? 0;

  return (
    <Card className={className}>
      <CardHeading title="Rating bands" subtitle={`How staff are grouped · ${rated} rated`} />
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {bands.map((b) => (
          <li key={b.band} className={`flex items-center gap-3 rounded-[1.1rem] px-3.5 py-3 ${BAND_TILE[b.band]}`}>
            <Chip tone={BAND_TONE[b.band]}>{b.band}</Chip>
            <span className="flex-1 text-[0.78rem] font-bold text-slate-700">{b.range}</span>
            <span className={`${bigNumber} text-[1.6rem]`}>{b.count}</span>
          </li>
        ))}
      </ul>
      <Note tone="alert" className="mt-auto">
        <b className="font-extrabold">{poor} staff</b> are rated Poor. Review their contributing complaints before any
        award decision.
      </Note>
    </Card>
  );
}
