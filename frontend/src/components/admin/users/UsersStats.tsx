import { Card, bigNumber, eyebrow } from "../dashboard/ui";
import { ROLE_ORDER } from "./staff";
import type { UsersSummary } from "./types";

// One colour per role for the share bar, in ROLE_ORDER.
const BAR_COLORS = ["bg-white", "bg-[#ffd6df]", "bg-[#ff9db0]", "bg-[#ffe9ed]", "bg-white/50"];

// The strip of figures above the directory.
export function UsersStats({ summary }: { summary: UsersSummary }) {
  const { active, signedInNow, locked, inactive, byRole } = summary;

  return (
    <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
      <section className="relative flex min-h-[11.9rem] min-w-0 flex-col justify-between gap-4 overflow-hidden rounded-[2rem] bg-[linear-gradient(135deg,#650720_0%,#A8102F_58%,#cf2a4b_100%)] p-7 text-white shadow-[0_34px_60px_-36px_rgba(110,8,30,0.75)] min-[1200px]:col-span-5">
        <div
          aria-hidden="true"
          className="absolute -right-[4.4rem] -top-[5.6rem] size-[17.5rem] rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.2),transparent_65%)]"
        />
        <div className="relative">
          <p className="text-[0.69rem] font-bold uppercase tracking-[0.1em] text-white/75">Users</p>
          <p className="mt-1.5 flex items-baseline gap-2.5">
            <span className={`${bigNumber} text-[4rem]`}>{active}</span>
            <span className="text-[0.88rem] font-semibold text-white/85">active staff</span>
          </p>
        </div>
        <div
          className="relative flex h-2 gap-0.5 overflow-hidden rounded-full"
          role="img"
          aria-label="Share of active staff by role"
        >
          {ROLE_ORDER.map((role, i) => (
            <div
              key={role}
              className={BAR_COLORS[i]}
              style={{ width: `${(byRole[role] / (active || 1)) * 100}%` }}
            />
          ))}
        </div>
      </section>

      <section className="flex min-w-0 flex-col justify-between gap-3 rounded-[1.75rem] bg-slate-ink p-6 text-white shadow-[0_26px_50px_-34px_rgba(20,28,40,0.7)] min-[1200px]:col-span-4">
        <p className="text-[0.69rem] font-bold uppercase tracking-[0.09em] text-white/65">
          Signed in now
        </p>
        <p className="flex items-baseline gap-2">
          <span className={`${bigNumber} text-[4rem]`}>{signedInNow}</span>
          <span className="text-[0.8rem] text-white/75">of {active} staff</span>
        </p>
        <p className="text-[0.78rem] text-white/70">Deactivating someone ends their session at once.</p>
      </section>

      <Card className="justify-center gap-3 min-[1200px]:col-span-3">
        <div>
          <p className={eyebrow}>Locked</p>
          <p className={`${bigNumber} mt-1 text-[2.25rem] ${locked ? "text-red-800" : ""}`}>{locked}</p>
        </div>
        <div>
          <p className={eyebrow}>Deactivated</p>
          <p className={`${bigNumber} mt-1 text-[2.25rem]`}>{inactive}</p>
        </div>
      </Card>
    </div>
  );
}
