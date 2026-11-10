import { formatNumber, plural } from "./format";
import type { AdminDashboardData } from "./types";
import { Card, CardHeading, Chip } from "./ui";

function Tile({ label, value, tint }: { label: string; value: number; tint: string }) {
  return (
    <div className={`rounded-[1.1rem] px-[0.9rem] py-3 ${tint}`}>
      <p className="text-[0.72rem] font-bold">{label}</p>
      <p className="font-display text-[1.5rem] tabular-nums">{formatNumber(value)}</p>
    </div>
  );
}

export function MasterDataSummary({
  data,
  className = "",
}: {
  data: AdminDashboardData["masterData"];
  className?: string;
}) {
  return (
    <Card className={`gap-3 ${className}`}>
      <CardHeading title="Master data" subtitle="Records in the system" />
      <div className="grid grid-cols-2 gap-2">
        <div className="col-span-2 flex items-baseline justify-between rounded-[1.1rem] bg-crimson/10 px-[0.9rem] py-3">
          <span className="text-[0.78rem] font-bold">People</span>
          <span className="font-display text-[1.9rem] tabular-nums">{formatNumber(data.people)}</span>
        </div>
        <Tile label="Vehicles" value={data.vehicles} tint="bg-stone-100" />
        <Tile label="Permits" value={data.permits} tint="bg-stone-100" />
        <Tile label="Routes, stands" value={data.routesAndStands} tint="bg-slate-100" />
        <Tile label="Categories" value={data.categories} tint="bg-slate-100" />
      </div>
      {data.vehiclesWithoutPermit > 0 && (
        <div className="self-start">
          <Chip tone="warn">{plural(data.vehiclesWithoutPermit, "vehicle")} without a permit</Chip>
        </div>
      )}
    </Card>
  );
}
