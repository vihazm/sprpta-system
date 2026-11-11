import { Card, CardHeading, Chip, StatusDot, bigNumber, muted } from "@/components/dashboard/ui";
import { AVATAR_TINT, initials } from "./staff";
import type { AreaOfficer } from "./types";

// Who decides each area. An area with no active Level 2 officer offers to assign one.
export function AreaCoverage({
  areas,
  onAssign,
}: {
  areas: AreaOfficer[];
  onAssign: (area: AreaOfficer) => void;
}) {
  const uncovered = areas.filter((area) => !area.officerName).length;

  return (
    <Card>
      <CardHeading
        title="Level 2 coverage"
        subtitle="One active officer decides each area"
        action={
          uncovered ? <Chip tone="crit">{uncovered} uncovered</Chip> : <Chip tone="ok">All covered</Chip>
        }
      />
      <ul className="m-0 flex list-none flex-col gap-3 p-0">
        {areas.map((area) =>
          area.officerName ? (
            <li key={area.id} className="flex items-center gap-3 rounded-[1.1rem] bg-[#f7f4f5] px-3.5 py-2.5">
              <div
                className={`flex size-9 flex-none items-center justify-center rounded-full text-[0.75rem] font-extrabold ${AVATAR_TINT.l2}`}
              >
                {initials(area.officerName)}
              </div>
              <div className="min-w-0 flex-1">
                <p className={`${bigNumber} text-[1.25rem]`}>{area.name}</p>
                <p className={`truncate ${muted}`}>{area.officerName}</p>
              </div>
              <StatusDot tone="ok" />
            </li>
          ) : (
            <li
              key={area.id}
              className="flex items-center gap-3 rounded-[1.1rem] border-[1.5px] border-dashed border-[#e2a6b2] bg-[#fdf3f5] px-3.5 py-2.5"
            >
              <div className="min-w-0 flex-1">
                <p className={`${bigNumber} text-[1.25rem]`}>{area.name}</p>
                <p className="text-[0.75rem] font-bold text-red-800">No active officer</p>
              </div>
              <button
                type="button"
                onClick={() => onAssign(area)}
                className="focus-ring h-[1.9rem] cursor-pointer whitespace-nowrap rounded-full border-[1.5px] border-crimson bg-crimson px-3 text-[0.75rem] font-bold text-white transition-colors hover:bg-crimson-hover"
              >
                Assign an officer
              </button>
            </li>
          ),
        )}
      </ul>
    </Card>
  );
}
