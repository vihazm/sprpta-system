"use client";

import { useEffect, useRef, useState } from "react";
import { formatNumber } from "@/components/admin/dashboard/format";
import { BarRows } from "@/components/dashboard/BarRows";
import { Field, inputClass } from "@/components/dashboard/controls";
import { Note } from "@/components/dashboard/Note";
import { SEVERITY_COLOR } from "@/components/dashboard/severity";
import { StatBox } from "@/components/dashboard/StatBox";
import { Card, CardHeading, PillButton, muted } from "@/components/dashboard/ui";
import { Icon } from "@/components/dashboard/icons";
import { statusName } from "../complaint-status";
import { loadStatistics, type CountRow, type Filters, type Option, type Statistics } from "./api";
import { download, statisticsCsv } from "./csv";
import { PERIODS, periodDates, type Period } from "./period";
import { TimeTargets } from "./TimeTargets";

const SEVERITY_COLORS = Object.values(SEVERITY_COLOR); // Critical to Low

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const monthName = (key: string) => `${MONTHS[Number(key.slice(5)) - 1]} ${key.slice(0, 4)}`;

function bars(rows: CountRow[], label: (key: string) => string = String, color?: (key: string) => string | undefined) {
  const widest = Math.max(1, ...rows.map((r) => r.count));
  return rows.map((r) => ({ label: label(r.key), value: r.count, share: (r.count / widest) * 100, color: color?.(r.key) }));
}

function BreakdownCard({
  title,
  subtitle,
  items,
  labelWidth = "7.5rem",
  className = "",
}: {
  title: string;
  subtitle: string;
  items: ReturnType<typeof bars>;
  labelWidth?: string;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeading title={title} subtitle={subtitle} />
      {items.length > 0 ? <BarRows items={items} labelWidth={labelWidth} gap="gap-3" /> : <p className={muted}>Nothing to count.</p>}
    </Card>
  );
}

function Select({ id, label, all, options, value, onChange }: {
  id: string;
  label: string;
  all: string;
  options: Option[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <Field label={label} htmlFor={id}>
      <select id={id} className={inputClass} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{all}</option>
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </Field>
  );
}

// Statistics and reports for the administrator (UI-AD-11): the same measures as Level 3's statistics, with
// personal data masked. The figures are counts and days only, so there is nothing personal to show.
export function StatisticsView({ initial, initialFilters }: { initial: Statistics; initialFilters: Filters }) {
  const [filters, setFilters] = useState(initialFilters);
  const [period, setPeriod] = useState<Period>("12m");
  const [stats, setStats] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const firstShown = useRef(true); // the page came with the figures for the first filters
  useEffect(() => {
    if (firstShown.current) {
      firstShown.current = false;
      return;
    }
    let current = true;
    setLoading(true);
    void loadStatistics(filters).then((result) => {
      if (!current) return; // a newer request has replaced this one
      setLoading(false);
      setError(result.ok ? null : result.message);
      if (result.ok) setStats(result.data);
    });
    return () => {
      current = false;
    };
  }, [filters]);

  const change = (patch: Partial<Filters>) => setFilters((f) => ({ ...f, ...patch }));

  function choosePeriod(value: Exclude<Period, "custom">) {
    setPeriod(value);
    change(periodDates(value));
  }

  function changeDate(patch: Partial<Filters>) {
    setPeriod("custom");
    change(patch);
  }

  function reset() {
    setPeriod("12m");
    setFilters({ ...periodDates("12m"), areaId: "", categoryId: "", severityId: "", mediumId: "" });
  }

  function exportCsv() {
    const named = (options: Option[], id: string, all: string) => options.find((o) => String(o.id) === id)?.name ?? all;
    const { options } = stats;
    const described = [
      filters.from || filters.to ? `${filters.from || "the start"} to ${filters.to || "today"}` : "All time",
      named(options.areas, filters.areaId, "All areas"),
      named(options.categories, filters.categoryId, "All categories"),
      named(options.severities, filters.severityId, "All severities"),
      named(options.mediums, filters.mediumId, "All mediums"),
    ];
    const csv = statisticsCsv(stats, described, { status: statusName });
    download(csv, `sprpta-statistics-${filters.from || "start"}-to-${filters.to || "today"}.csv`);
  }

  const count = (key: string) => stats.byStatus.find((s) => s.key === key)?.count ?? 0;
  const closed = count("closed");
  const rejected = count("rejected");
  const open = stats.total - closed - rejected;
  // Severities can be renamed, so the colour follows the position in the list (Critical first).
  const severityColor = (name: string) => SEVERITY_COLORS[stats.options.severities.findIndex((s) => s.name === name)];

  return (
    <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
      <Card className="min-[1200px]:col-span-12">
        <CardHeading
          title="Complaint statistics"
          subtitle="Registered complaints, counted by the database. Personal data is never shown here."
          action={
            <PillButton primary onClick={exportCsv} disabled={loading}>
              <Icon name="download" size={14} />
              Export CSV
            </PillButton>
          }
        />
        <div className="flex flex-wrap items-center gap-2">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              type="button"
              aria-pressed={period === p.value}
              onClick={() => choosePeriod(p.value)}
              className={`focus-ring cursor-pointer rounded-full border-[1.5px] px-[0.95rem] py-2 text-[0.78rem] font-bold transition-colors ${
                period === p.value ? "border-ink bg-ink text-white" : "border-[#E5E7EB] bg-white text-slate-ink hover:border-crimson"
              }`}
            >
              {p.label}
            </button>
          ))}
          <button
            type="button"
            onClick={reset}
            className="focus-ring ml-auto cursor-pointer text-[0.78rem] font-extrabold text-crimson-hover hover:underline"
          >
            Reset filters
          </button>
        </div>
        <div className="grid grid-cols-1 gap-3 min-[640px]:grid-cols-3 min-[1200px]:grid-cols-6">
          <Field label="From" htmlFor="stats-from">
            <input id="stats-from" type="date" className={inputClass} value={filters.from} max={filters.to || undefined} onChange={(e) => changeDate({ from: e.target.value })} />
          </Field>
          <Field label="To" htmlFor="stats-to">
            <input id="stats-to" type="date" className={inputClass} value={filters.to} min={filters.from || undefined} onChange={(e) => changeDate({ to: e.target.value })} />
          </Field>
          <Select id="stats-area" label="Area" all="All areas" options={stats.options.areas} value={filters.areaId} onChange={(areaId) => change({ areaId })} />
          <Select id="stats-category" label="Category" all="All categories" options={stats.options.categories} value={filters.categoryId} onChange={(categoryId) => change({ categoryId })} />
          <Select id="stats-severity" label="Severity" all="All severities" options={stats.options.severities} value={filters.severityId} onChange={(severityId) => change({ severityId })} />
          <Select id="stats-medium" label="Medium" all="All mediums" options={stats.options.mediums} value={filters.mediumId} onChange={(mediumId) => change({ mediumId })} />
        </div>
        {error && <Note tone="alert">{error}</Note>}
      </Card>

      <div
        aria-busy={loading}
        className={`grid grid-cols-1 gap-4 transition-opacity min-[1200px]:col-span-12 min-[1200px]:grid-cols-12 ${loading ? "opacity-60" : ""}`}
      >
        <Card className="min-[1200px]:col-span-12">
          <div className="grid grid-cols-2 gap-2.5 min-[900px]:grid-cols-5">
            <StatBox label="Registered" value={formatNumber(stats.total)} note="In the chosen period" />
            <StatBox label="Open" value={formatNumber(open)} note="Not closed or rejected" />
            <StatBox label="Closed" value={formatNumber(closed)} note="Approved and closed" />
            <StatBox label="Rejected" value={formatNumber(rejected)} note="Invalid, spam, duplicate or out of area" />
            <StatBox label="Overdue now" value={formatNumber(stats.overdue.total)} note="Open cases past a target" />
          </div>
        </Card>

        {stats.total === 0 ? (
          <Card className="min-[1200px]:col-span-12">
            <p className={muted}>No registered complaint matches these filters. Try a longer period or fewer filters.</p>
          </Card>
        ) : (
          <>
            <BreakdownCard title="By status" subtitle="Where the complaints are now" items={bars(stats.byStatus, statusName)} labelWidth="11rem" className="min-[1200px]:col-span-6" />
            <BreakdownCard title="By month" subtitle="Month of registration" items={bars(stats.byMonth, monthName)} labelWidth="5.5rem" className="min-[1200px]:col-span-6" />
            <BreakdownCard title="By area" subtitle="The vehicle's registered area" items={bars(stats.byArea)} className="min-[1200px]:col-span-4" />
            <BreakdownCard title="By category" subtitle="What the complaints are about" items={bars(stats.byCategory)} labelWidth="9rem" className="min-[1200px]:col-span-4" />
            <BreakdownCard title="By severity" subtitle="As set by Level 1" items={bars(stats.bySeverity, String, severityColor)} className="min-[1200px]:col-span-4" />
            <BreakdownCard title="By medium" subtitle="How the complaints arrived" items={bars(stats.byMedium)} className="min-[1200px]:col-span-4" />
            <TimeTargets stats={stats} className="min-[1200px]:col-span-8" />
          </>
        )}
      </div>
    </div>
  );
}
