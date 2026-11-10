import { sum } from "./format";
import type { Count } from "./types";
import { Card, CardHeading, Chip, bigNumber } from "./ui";

// Each role gets its own soft tint and bar colour, in the order the roles are listed.
const TILE_TINTS = ["bg-crimson/10", "bg-crimson/5", "bg-stone-100", "bg-slate-100", "bg-stone-100"];
const BAR_COLORS = ["bg-crimson", "bg-rose-400", "bg-red-900", "bg-slate-800", "bg-slate-400"];

export function StaffByRole({
  roles,
  portalUsers,
  deactivatedUsers,
  className = "",
}: {
  roles: Count[];
  portalUsers: { total: number; unverified: number };
  deactivatedUsers: number;
  className?: string;
}) {
  const total = sum(roles);

  return (
    <Card className={className}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <CardHeading title="Staff by role" subtitle={`${total} active staff accounts`} />
        <div className="flex flex-wrap gap-[0.4rem]">
          <Chip>{portalUsers.total} portal users</Chip>
          <Chip tone="warn">{portalUsers.unverified} unverified</Chip>
          <Chip>{deactivatedUsers} deactivated</Chip>
        </div>
      </div>

      <ul className="grid flex-1 list-none grid-cols-2 gap-3 p-0 sm:grid-cols-5">
        {roles.map((role, i) => (
          <li
            key={role.label}
            className={`flex min-w-0 flex-col justify-between gap-4 rounded-[1.4rem] px-4 pb-[0.9rem] pt-4 ${TILE_TINTS[i % TILE_TINTS.length]}`}
          >
            <p className={`${bigNumber} text-[2.75rem]`}>{role.count}</p>
            <div className="flex flex-col gap-[0.6rem]">
              <p className="text-[0.78rem] font-bold leading-[1.25]">{role.label}</p>
              <div className="h-[0.38rem] rounded-full bg-white/70">
                <div
                  className={`h-full rounded-full ${BAR_COLORS[i % BAR_COLORS.length]}`}
                  style={{ width: `${(role.count / (total || 1)) * 100}%` }}
                />
              </div>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
