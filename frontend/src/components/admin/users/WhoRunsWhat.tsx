import { bigNumber } from "@/components/dashboard/ui";
import { Icon } from "@/components/dashboard/icons";
import type { StatusFilter } from "./staff";
import type { UsersSummary } from "./types";

const CHIPS: { value: Exclude<StatusFilter, null>; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "locked", label: "Locked" },
];

// The crimson box above the coverage tile. Its search and status chips filter the directory.
export function WhoRunsWhat({
  summary,
  query,
  onQuery,
  status,
  onStatus,
}: {
  summary: UsersSummary;
  query: string;
  onQuery: (query: string) => void;
  status: StatusFilter;
  onStatus: (status: StatusFilter) => void;
}) {
  return (
    <section className="relative flex min-w-0 flex-col gap-4 overflow-hidden rounded-[1.75rem] bg-[linear-gradient(135deg,#650720_0%,#A8102F_58%,#cf2a4b_100%)] p-6 text-white shadow-[0_34px_60px_-36px_rgba(110,8,30,0.75)]">
      <div
        aria-hidden="true"
        className="absolute -right-[4.4rem] -top-[5.6rem] size-[16rem] rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.2),transparent_65%)]"
      />
      <div className="relative">
        <p className="text-[0.69rem] font-bold uppercase tracking-[0.1em] text-white/75">Users</p>
        <h2 className={`${bigNumber} mt-1.5 text-[2rem] leading-[1.02]`}>Who runs what</h2>
      </div>
      <p className="relative text-[0.82rem] leading-[1.45] text-white/90">
        {summary.active} active staff, grouped by role. Every area needs one Level 2
        officer.
      </p>

      <label className="relative flex h-[2.6rem] items-center gap-2.5 rounded-full bg-white px-4 text-muted focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-white">
        <span className="sr-only">Search users</span>
        <Icon name="search" size={16} />
        <input
          type="search"
          placeholder="Find someone by name, email or phone"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          className="h-10 min-w-0 flex-1 bg-transparent text-[0.8rem] font-medium text-ink outline-none"
        />
      </label>

      <div className="relative flex flex-wrap gap-[0.45rem]">
        {CHIPS.map((chip) => (
          <button
            key={chip.value}
            type="button"
            aria-pressed={status === chip.value}
            onClick={() => onStatus(status === chip.value ? null : chip.value)}
            className={`focus-ring inline-flex cursor-pointer items-center gap-[0.45rem] rounded-full border px-[0.8rem] py-1.5 text-[0.78rem] font-bold transition-colors ${
              status === chip.value
                ? "border-white/50 bg-white/20 text-white"
                : "border-white/30 text-white/90 hover:bg-white/10"
            }`}
          >
            {chip.label}
            <span className="font-semibold opacity-80">{summary[chip.value]}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
