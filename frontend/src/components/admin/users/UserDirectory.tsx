"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Card, Chip, StatusDot, muted } from "@/components/dashboard/ui";
import { AreaCoverage } from "./AreaCoverage";
import { Collapse } from "./Collapse";
import { CoverageStrip } from "./CoverageStrip";
import { EditUserPanel, type Preset } from "./EditUserPanel";
import { WhoRunsWhat } from "./WhoRunsWhat";
import { loadUsers } from "./api";
import { iconButton } from "@/components/dashboard/controls";
import { formatWhen } from "./format";
import { Icon } from "@/components/dashboard/icons";
import {
  AVATAR_TINT,
  ROLE_ORDER,
  ROLE_SHORT,
  STATUS_LABEL,
  STATUS_TONE,
  type StatusFilter,
  initials,
} from "./staff";
import type { StaffRole, StaffUser, UserPage, UsersSummary } from "./types";

const th = "px-2.5 py-1 text-left text-[0.69rem] font-bold uppercase tracking-[0.07em] text-muted";

// Which account the form is for (null for a new user), and an optional pre-fill.
// The panel stays set while the form slides shut, so its content does not vanish mid-animation.
type Panel = { key: number; user: StaffUser | null; preset?: Preset };

// The directory table, and beside it a column that holds the two boxes. When the form
// opens, the boxes shrink to a strip and the form slides in below it.
export function UserDirectory({ summary }: { summary: UsersSummary }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState(""); // the query, once typing has paused
  const [status, setStatus] = useState<StatusFilter>(null);
  const [role, setRole] = useState<StaffRole | "all">("all");
  const [page, setPage] = useState(1);
  const [reload, setReload] = useState(0); // bumped to fetch the table again after a change
  const [data, setData] = useState<UserPage | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [panel, setPanel] = useState<Panel | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(query.trim());
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    let current = true;
    loadUsers({ search, status, role, page }).then((result) => {
      if (!current) return; // a newer request has replaced this one
      setLoadError(result.ok ? null : result.message);
      if (result.ok) setData(result.data);
    });
    return () => {
      current = false;
    };
  }, [search, status, role, page, reload]);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  function openPanel(user: StaffUser | null, preset?: Preset) {
    setPanel({ key: (panel?.key ?? 0) + 1, user, preset });
    setOpen(true);
  }

  // After a save: close the form, fetch the table again, and refresh the figures above it.
  function saved() {
    setOpen(false);
    setReload((n) => n + 1);
    router.refresh();
  }

  // Any change to the filters starts again from the first page.
  function filterBy(change: () => void) {
    change();
    setPage(1);
  }

  const users = data?.users ?? [];
  const pageCount = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;
  const firstRow = data ? (data.page - 1) * data.pageSize : 0;
  const editedId = open ? panel?.user?.id : null;

  const tabs = data
    ? [
        { value: "all" as const, label: "All", count: data.roleCounts.all },
        ...ROLE_ORDER.map((r) => ({ value: r, label: ROLE_SHORT[r], count: data.roleCounts[r] })),
      ]
    : [];

  return (
    <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
      <Card className="gap-[0.9rem] min-[1200px]:col-span-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-[1.25rem] font-extrabold tracking-[-0.015em]">Directory</h2>
            <p className={`mt-0.5 ${muted}`}>Every staff account, grouped by role</p>
          </div>
          <button
            type="button"
            onClick={() => openPanel(null)}
            className="focus-ring inline-flex h-[2.4rem] cursor-pointer items-center gap-[0.45rem] whitespace-nowrap rounded-full border-[1.5px] border-crimson bg-crimson px-[1.05rem] text-[0.78rem] font-bold text-white transition-colors hover:bg-crimson-hover"
          >
            <Icon name="plus" size={14} />
            Create user
          </button>
        </div>

        <div className="flex flex-wrap gap-1 self-start rounded-full bg-field p-1">
          {tabs.map((tab) => (
            <button
              key={tab.value}
              type="button"
              aria-pressed={role === tab.value}
              onClick={() => filterBy(() => setRole(tab.value))}
              className={`focus-ring inline-flex cursor-pointer items-center gap-[0.45rem] rounded-full px-3.5 py-2 text-[0.78rem] font-bold transition-colors ${
                role === tab.value ? "bg-ink text-white" : "text-muted hover:text-ink"
              }`}
            >
              {tab.label}
              <span className="font-bold opacity-70">{tab.count}</span>
            </button>
          ))}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-separate border-spacing-y-1 text-[0.81rem]">
            <thead>
              <tr>
                <th className={th}>User</th>
                <th className={th}>Role</th>
                <th className={th}>Last sign-in</th>
                <th className={th}>Status</th>
                <th className={th}>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr
                  key={user.id}
                  onClick={() => openPanel(user)}
                  className={`cursor-pointer *:px-2.5 *:py-2.5 *:first:rounded-l-[1.1rem] *:last:rounded-r-[1.1rem] ${
                    editedId === user.id ? "*:bg-crimson/10" : "*:bg-white hover:*:bg-[#fbf5f6]"
                  }`}
                >
                  <td>
                    <div className="flex items-center gap-3">
                      <div
                        className={`flex size-10 flex-none items-center justify-center rounded-full text-[0.81rem] font-extrabold ${AVATAR_TINT[user.role]}`}
                      >
                        {initials(user.name)}
                      </div>
                      <div className="min-w-0">
                        <p className="text-[0.84rem] font-extrabold">{user.name}</p>
                        <p className={`${muted} max-w-[9.5rem] truncate`} title={user.login}>
                          {user.login}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div className="flex flex-col items-start gap-1">
                      <Chip tone="brand">{ROLE_SHORT[user.role]}</Chip>
                      {user.area && (
                        <span className="text-[0.75rem] font-semibold text-slate-700">{user.area}</span>
                      )}
                    </div>
                  </td>
                  <td className="tabular-nums text-slate-700">{formatWhen(user.lastSignIn)}</td>
                  <td>
                    <Chip tone={STATUS_TONE[user.status]}>
                      <StatusDot tone={STATUS_TONE[user.status]} />
                      {STATUS_LABEL[user.status]}
                    </Chip>
                  </td>
                  <td>
                    <div className="flex justify-end">
                      <button
                        type="button"
                        className={iconButton}
                        aria-label={`Edit ${user.name}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          openPanel(user);
                        }}
                      >
                        <Icon name="edit" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {(loadError || !data || users.length === 0) && (
            <p className="py-8 text-center text-[0.86rem] text-muted">
              {loadError ?? (data ? "No one matches these filters." : "Loading users…")}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className={muted}>
            {data && data.total > 0
              ? `Showing ${firstRow + 1} to ${firstRow + users.length} of ${data.total} users`
              : "No users to show"}
          </p>
          {data && pageCount > 1 && (
            <nav aria-label="Pages" className="flex gap-1.5">
              <button
                type="button"
                className={iconButton}
                aria-label="Previous page"
                disabled={data.page === 1}
                onClick={() => setPage(data.page - 1)}
              >
                <Icon name="prev" />
              </button>
              {Array.from({ length: pageCount }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  type="button"
                  aria-label={`Page ${n}`}
                  aria-current={n === data.page ? "page" : undefined}
                  className={`${iconButton} ${n === data.page ? "!border-ink !bg-ink !text-white" : ""}`}
                  onClick={() => setPage(n)}
                >
                  {n}
                </button>
              ))}
              <button
                type="button"
                className={iconButton}
                aria-label="Next page"
                disabled={data.page === pageCount}
                onClick={() => setPage(data.page + 1)}
              >
                <Icon name="next" />
              </button>
            </nav>
          )}
        </div>
      </Card>

      <div className="min-w-0 self-start min-[1200px]:col-span-4">
        <Collapse show={!open}>
          <WhoRunsWhat
            summary={summary}
            query={query}
            onQuery={setQuery}
            status={status}
            onStatus={(s) => filterBy(() => setStatus(s))}
          />
          <AreaCoverage
            areas={summary.areas}
            onAssign={(area) => openPanel(null, { role: "l2", areaId: area.id })}
          />
        </Collapse>
        <Collapse show={open}>
          <CoverageStrip summary={summary} />
        </Collapse>
        <Collapse show={open}>
          {panel && (
            <EditUserPanel
              key={panel.key}
              user={panel.user}
              preset={panel.preset}
              areas={summary.areas}
              onClose={() => setOpen(false)}
              onSaved={saved}
            />
          )}
        </Collapse>
      </div>
    </div>
  );
}
