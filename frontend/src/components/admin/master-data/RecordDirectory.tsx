"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { formatNumber } from "@/components/admin/dashboard/format";
import { Card, Chip, StatusDot, eyebrow, muted } from "@/components/dashboard/ui";
import { iconButton } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { loadRecords, type RecordPage, type Status } from "./api";
import { ENTITIES, type EntityKey, type Row } from "./entities";
import { RecordForm } from "./RecordForm";

const th = "px-2.5 py-1 text-left text-[0.69rem] font-bold uppercase tracking-[0.07em] text-muted";

const TABS: { value: Status; label: string; count: keyof RecordPage["counts"] }[] = [
  { value: null, label: "All", count: "all" },
  { value: "active", label: "Active", count: "active" },
  { value: "inactive", label: "Inactive", count: "inactive" },
];

// Which record the form is for: null while it is closed, "new" for a record being added.
type Editing = { key: number; row: Row | null } | null;

// The list and form of one kind of master data (UI-AD-05): search, filter by status, page through, and add or edit
// in the panel beside the table.
export function RecordDirectory({ entityKey, initial }: { entityKey: EntityKey; initial?: RecordPage }) {
  const entity = ENTITIES[entityKey];
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState(""); // the query, once typing has paused
  const [status, setStatus] = useState<Status>(null);
  const [page, setPage] = useState(1);
  const [reload, setReload] = useState(0); // bumped to fetch the table again after a save
  const [data, setData] = useState<RecordPage | null>(initial ?? null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Editing>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(query.trim());
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  const firstPageShown = useRef(initial !== undefined);
  useEffect(() => {
    if (firstPageShown.current) {
      firstPageShown.current = false; // the page already came with its first page
      return;
    }
    let current = true;
    void loadRecords(entityKey, { search, status, page }).then((result) => {
      if (!current) return; // a newer request has replaced this one
      setLoadError(result.ok ? null : result.message);
      if (result.ok) setData(result.data);
    });
    return () => {
      current = false;
    };
  }, [entityKey, search, status, page, reload]);

  useEffect(() => {
    if (!editing) return;
    const closeOnEscape = (e: KeyboardEvent) => e.key === "Escape" && setEditing(null);
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [editing]);

  const open = (row: Row | null) => setEditing({ key: (editing?.key ?? 0) + 1, row });

  function saved() {
    setEditing(null);
    setReload((n) => n + 1);
  }

  const rows = data?.items ?? [];
  const pageCount = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const firstRow = data ? (data.page - 1) * data.page_size : 0;
  const [nameColumn, ...otherColumns] = entity.columns;

  return (
    <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
      <Card className="gap-[0.9rem] min-[1200px]:col-span-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Link href="/admin/master-data" className={`${eyebrow} focus-ring rounded hover:text-crimson`}>
              ‹ Master data
            </Link>
            <h2 className="mt-1 text-[1.25rem] font-extrabold tracking-[-0.015em]">{entity.title}</h2>
          </div>
          {entity.canAdd && (
            <button
              type="button"
              onClick={() => open(null)}
              className="focus-ring inline-flex h-[2.4rem] cursor-pointer items-center gap-[0.45rem] whitespace-nowrap rounded-full border-[1.5px] border-crimson bg-crimson px-[1.05rem] text-[0.78rem] font-bold text-white transition-colors hover:bg-crimson-hover"
            >
              <Icon name="plus" size={14} />
              Add {entity.singular}
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex gap-1 rounded-full bg-field p-1">
            {TABS.map((tab) => (
              <button
                key={tab.label}
                type="button"
                aria-pressed={status === tab.value}
                onClick={() => {
                  setStatus(tab.value);
                  setPage(1);
                }}
                className={`focus-ring inline-flex cursor-pointer items-center gap-[0.45rem] rounded-full px-3.5 py-2 text-[0.78rem] font-bold transition-colors ${
                  status === tab.value ? "bg-ink text-white" : "text-muted hover:text-ink"
                }`}
              >
                {tab.label}
                {data && <span className="font-bold opacity-70">{formatNumber(data.counts[tab.count])}</span>}
              </button>
            ))}
          </div>
          <label className="flex h-[2.5rem] w-full max-w-[20rem] items-center gap-2.5 rounded-full bg-field px-4 text-muted focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-crimson">
            <span className="sr-only">Search {entity.title.toLowerCase()}</span>
            <Icon name="search" size={16} />
            <input
              type="search"
              placeholder={`Search ${entity.title.toLowerCase()}`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="h-10 min-w-0 flex-1 bg-transparent text-[0.8rem] font-medium text-ink outline-none"
            />
          </label>
        </div>

        <div className="relative overflow-x-auto">
          <table className="w-full border-separate border-spacing-y-1 text-[0.81rem]">
            <thead>
              <tr>
                {entity.columns.map((c) => (
                  <th key={c.label} className={th}>
                    {c.label}
                  </th>
                ))}
                <th className={th}>Status</th>
                <th className={th}>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => open(row)}
                  className={`cursor-pointer *:px-2.5 *:py-2.5 *:first:rounded-l-[1.1rem] *:last:rounded-r-[1.1rem] ${
                    editing?.row?.id === row.id ? "*:bg-crimson/10" : "*:bg-white hover:*:bg-[#fbf5f6]"
                  }`}
                >
                  <td className="font-extrabold">{nameColumn.value(row)}</td>
                  {otherColumns.map((c) => (
                    <td key={c.label} className="max-w-[14rem] truncate text-slate-700">
                      {c.value(row) ?? <span className="text-muted">—</span>}
                    </td>
                  ))}
                  <td>
                    <Chip tone={row.is_active ? "ok" : "info"}>
                      <StatusDot tone={row.is_active ? "ok" : "info"} />
                      {row.is_active ? "Active" : "Inactive"}
                    </Chip>
                  </td>
                  <td>
                    <div className="flex justify-end">
                      <button
                        type="button"
                        className={iconButton}
                        aria-label={`Edit ${nameColumn.value(row)}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          open(row);
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
          {(loadError || !data || rows.length === 0) && (
            <p className="py-8 text-center text-[0.86rem] text-muted">
              {loadError ?? (data ? "Nothing matches this search." : "Loading…")}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className={muted}>
            {data && data.total > 0
              ? `Showing ${formatNumber(firstRow + 1)} to ${formatNumber(firstRow + rows.length)} of ${formatNumber(data.total)}`
              : "Nothing to show"}
          </p>
          {data && pageCount > 1 && (
            <nav aria-label="Pages" className="flex items-center gap-2">
              <button
                type="button"
                className={iconButton}
                aria-label="Previous page"
                disabled={data.page === 1}
                onClick={() => setPage(data.page - 1)}
              >
                <Icon name="prev" />
              </button>
              <span className="text-[0.78rem] font-bold tabular-nums">
                Page {formatNumber(data.page)} of {formatNumber(pageCount)}
              </span>
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

      <div className="flex min-w-0 flex-col gap-4 self-start min-[1200px]:col-span-4">
        {editing ? (
          <RecordForm
            key={editing.key}
            entityKey={entityKey}
            row={editing.row}
            onClose={() => setEditing(null)}
            onSaved={saved}
          />
        ) : (
          <Card className="gap-3">
            <p className={eyebrow}>Before you edit</p>
            <ul className="m-0 flex list-disc flex-col gap-2 pl-4 text-[0.8rem] leading-[1.5] text-slate-ink">
              {entity.rules.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
            <p className={muted}>Choose a row to edit it. Every change is recorded in the audit trail.</p>
          </Card>
        )}
      </div>
    </div>
  );
}
