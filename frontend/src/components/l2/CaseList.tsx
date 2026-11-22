"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { inputClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { Note } from "@/components/dashboard/Note";
import { OverdueBadge } from "@/components/dashboard/OverdueBadge";
import { SeverityChip, SEVERITY_LABEL, type Severity } from "@/components/dashboard/severity";
import { Card, CardHeading, PillButton, muted } from "@/components/dashboard/ui";
import { listCases } from "./api";
import { dayMonth, dayMonthTime, dueText } from "./format";
import { STATUS_LABEL, STATUS_ORDER, StatusTag } from "./status";
import type { CaseFilter, CasePage, CaseRow, CaseSort } from "./types";

const TABS: { filter: CaseFilter | null; label: string }[] = [
  { filter: null, label: "All" },
  ...STATUS_ORDER.map((status) => ({ filter: status, label: STATUS_LABEL[status] })),
  { filter: "overdue", label: "Overdue" },
];
const SEVERITIES: (Severity | null)[] = [null, "critical", "high", "medium", "low"];

// The Cases page also shows when each case was forwarded; beside the dashboard's case card there is less room.
const columnsFor = (wide: boolean) =>
  `grid items-center gap-3 ${
    wide
      ? "grid-cols-[10.5rem_minmax(0,1fr)_5.5rem_5.25rem_11.5rem_9.5rem]"
      : "grid-cols-[9.75rem_minmax(0,1fr)_4.75rem_10.5rem_8.5rem]"
  }`;
const th = (wide: boolean) =>
  `${wide ? "text-[0.76rem]" : "text-[0.69rem]"} font-bold uppercase tracking-[0.07em] text-muted`;

// The area's cases (UI-L2-02), searchable and filterable by status, severity and Overdue. On the dashboard a row
// picks the case shown beside the list (onSelect); on the Cases page a row opens the case.
export function CaseList({
  title,
  subtitle,
  status,
  onStatus,
  sort: initialSort = "urgent",
  initial,
  selected,
  onSelect,
  className = "",
}: {
  title: string;
  subtitle: string;
  status: CaseFilter | null;
  onStatus: (status: CaseFilter | null) => void;
  sort?: CaseSort;
  initial?: CasePage; // the first view, read with the page, so it needs no request of its own
  selected?: number | null;
  onSelect?: (row: CaseRow) => void;
  className?: string;
}) {
  const [typed, setTyped] = useState("");
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState<Severity | null>(null);
  const [sort, setSort] = useState<CaseSort>(initialSort);
  const [page, setPage] = useState(1);
  const key = `${status}|${severity}|${search}|${sort}|${page}`;
  const [answer, setAnswer] = useState<{ key: string; page?: CasePage; error?: string } | null>(
    initial ? { key, page: initial } : null,
  );
  const firstViewShown = useRef(initial !== undefined);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(typed.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [typed]);

  useEffect(() => {
    if (firstViewShown.current) {
      firstViewShown.current = false;
      return;
    }
    let current = true;
    void listCases({ status, severity, search, sort, page }).then((result) => {
      if (current) setAnswer(result.ok ? { key, page: result.data } : { key, error: result.message });
    });
    return () => {
      current = false;
    };
  }, [status, severity, search, sort, page, key]);

  const wide = onSelect === undefined;
  const loading = answer?.key !== key;
  const data = answer?.page;
  const pages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;
  const firstRow = data ? (data.page - 1) * data.pageSize : 0;

  function nextSeverity() {
    setSeverity(SEVERITIES[(SEVERITIES.indexOf(severity) + 1) % SEVERITIES.length]);
    setPage(1);
  }

  return (
    <Card className={className}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <CardHeading title={title} subtitle={subtitle} />
        <div className="flex flex-wrap items-center gap-2">
          <label className="relative block">
            <span className="sr-only">Search cases</span>
            <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted">
              <Icon name="search" size={14} />
            </span>
            <input
              type="search"
              className={`${inputClass} !h-[2.1rem] !w-[15rem] !rounded-full !pl-9 !text-[0.78rem]`}
              placeholder="Search reference, vehicle, subject"
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
            />
          </label>
          <PillButton onClick={nextSeverity}>Severity: {severity ? SEVERITY_LABEL[severity] : "All"}</PillButton>
          <PillButton
            onClick={() => {
              setSort(sort === "urgent" ? "newest" : "urgent");
              setPage(1);
            }}
          >
            Sort: {sort === "urgent" ? "Most urgent" : "Newest"}
          </PillButton>
        </div>
      </div>

      <div className="flex flex-wrap gap-2" role="group" aria-label="Status">
        {TABS.map((tab) => (
          <PillButton
            key={tab.label}
            primary={status === tab.filter}
            onClick={() => {
              setPage(1);
              onStatus(tab.filter);
            }}
          >
            {tab.label}
            {data && <span className="tabular-nums opacity-80">· {data.counts[tab.filter ?? "all"] ?? 0}</span>}
          </PillButton>
        ))}
      </div>

      {answer?.error && <Note tone="alert">{answer.error}</Note>}

      <div className="overflow-x-auto">
        <div className={`${wide ? "min-w-[58rem]" : "min-w-[46rem]"} transition-opacity ${loading ? "opacity-60" : ""}`}>
          <div className={`${columnsFor(wide)} px-3 pb-1`}>
            <span className={th(wide)}>Reference</span>
            <span className={th(wide)}>Subject</span>
            {wide && <span className={th(wide)}>Forwarded</span>}
            <span className={th(wide)}>Severity</span>
            <span className={th(wide)}>Status</span>
            <span className={th(wide)}>Next target</span>
          </div>
          <ul className="m-0 flex list-none flex-col gap-0.5 p-0">
            {data?.items.map((c) => (
              <li key={c.id}>
                <Row c={c} wide={wide} on={c.id === selected} onSelect={onSelect} />
              </li>
            ))}
          </ul>
          {!data && !answer?.error && <p className="py-8 text-center text-[0.86rem] text-muted">Loading cases…</p>}
          {data?.items.length === 0 && (
            <p className="py-8 text-center text-[0.86rem] text-muted">
              {search ? "No case matches your search." : "No cases here in your area."}
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#f1ebed] pt-3">
        <p className={muted}>
          {data && data.total > 0
            ? `Showing ${firstRow + 1} to ${firstRow + data.items.length} of ${data.total}. Cases past your steps are read-only.`
            : "Nothing to show"}
        </p>
        {data && pages > 1 && (
          <div className="flex gap-2">
            <PillButton disabled={data.page === 1} onClick={() => setPage(data.page - 1)}>
              <Icon name="prev" size={12} />
              Previous
            </PillButton>
            <PillButton disabled={data.page === pages} onClick={() => setPage(data.page + 1)}>
              Next
              <Icon name="next" size={12} />
            </PillButton>
          </div>
        )}
      </div>
    </Card>
  );
}

function Row({
  c,
  wide,
  on,
  onSelect,
}: {
  c: CaseRow;
  wide: boolean;
  on: boolean;
  onSelect?: (row: CaseRow) => void;
}) {
  const look = `focus-ring ${columnsFor(wide)} w-full cursor-pointer rounded-[1.1rem] border-[1.5px] px-3 py-2.5 text-left transition-colors duration-100 ${
    on
      ? "border-crimson bg-white"
      : c.overdue
        ? "border-transparent bg-red-50 hover:bg-red-100/70"
        : "border-transparent hover:bg-[#f7f4f5]"
  }`;
  const cells = (
    <>
      <b className={`whitespace-nowrap font-extrabold text-crimson-hover ${wide ? "text-[0.85rem]" : "text-[0.75rem]"}`}>
        {c.reference}
      </b>
      <span className="min-w-0">
        <span className={`block truncate font-bold ${wide ? "text-[1rem]" : "text-[0.81rem]"}`}>
          {c.subject ?? "No subject"}
        </span>
        <span className={`font-bold text-muted ${wide ? "text-[0.78rem]" : "text-[0.69rem]"}`}>
          {c.vehicle ?? "No vehicle"}
        </span>
      </span>
      {wide && <span className="text-[0.85rem] font-bold text-slate-600">{dayMonth(c.forwardedAt)}</span>}
      <span>
        <SeverityChip severity={c.severity} large={wide} />
      </span>
      <span className="flex flex-wrap items-center gap-1.5">
        <StatusTag status={c.status} large={wide} />
        {c.overdue && <OverdueBadge large={wide} />}
      </span>
      <span className="min-w-0">
        <span
          suppressHydrationWarning // counted from the current time, which moves on between server and browser
          className={`block font-extrabold ${wide ? "text-[0.85rem]" : "text-[0.75rem]"} ${c.overdue ? "text-red-800" : "text-slate-600"}`}
        >
          {dueText(c)}
        </span>
        {c.dueAt && (
          <span className={`font-bold text-muted ${wide ? "text-[0.78rem]" : "text-[0.69rem]"}`}>
            {dayMonthTime(c.dueAt)}
          </span>
        )}
      </span>
    </>
  );

  return onSelect ? (
    <button type="button" aria-pressed={on} onClick={() => onSelect(c)} className={look}>
      {cells}
    </button>
  ) : (
    <Link href={`/l2/cases/${c.id}`} className={look}>
      {cells}
    </Link>
  );
}
