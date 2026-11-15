"use client";

import { useEffect, useState } from "react";
import { inputClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, Chip, PillButton, PillLink, muted } from "@/components/dashboard/ui";
import { listComplaints, type ComplaintFilter, type ComplaintPage, type TargetFilter } from "@/components/l1/dashboard/api";
import { STATUS_TONE } from "@/components/l1/status";

const th = "px-2.5 py-1 text-left text-[0.69rem] font-bold uppercase tracking-[0.07em] text-muted";

const TABS: { filter: ComplaintFilter | null; label: string }[] = [
  { filter: null, label: "All" },
  { filter: "draft", label: "Drafts" },
  { filter: "incomplete", label: "Incomplete" },
  { filter: "duplicates", label: "Possible duplicates" },
  { filter: "submitted", label: "Portal submissions" },
  { filter: "forwarded", label: "Forwarded" },
  { filter: "rejected", label: "Rejected" },
];

const TARGET_TABS: { target: TargetFilter | null; label: string }[] = [
  { target: null, label: "All" },
  { target: "driver", label: "Driver" },
  { target: "conductor", label: "Conductor" },
  { target: "owner", label: "Owner" },
  { target: "bus_service", label: "Bus / Service" },
  { target: "other", label: "Other" },
];

function day(iso: string | null) {
  if (!iso) return "–";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

const VERIFICATION_LABEL: Record<string, string> = {
  not_found: "Bus not found",
  not_operated: "Bus did not operate",
  trip_cancelled: "Trip cancelled",
  unverified: "Not verified",
};

// What the mark beside an accused person means. Only the server decides it.
const ACCUSED_NOTE: Record<string, string> = {
  verified_duty: "Verified on duty for this trip",
  registered_owner: "Registered owner of the bus",
  directory_only: "In the directory, not verified for this trip",
  unidentified: "Written by the officer, not matched to a record",
};

// The Level 1 list of complaints: one table for the Complaints page, for the dashboard cards that open a filtered
// view of it, and (with a fixed filter and no tabs) for Portal submissions. Drafts and incomplete cases open in the
// form to be finished; everything else is read-only.
export function ComplaintsList({
  title,
  subtitle,
  filter,
  onFilter,
  target = null,
  onTarget,
  scope = "mine",
  categoryId = null,
  verification = null,
  onClearFilter,
  fixed = false,
  emptyText,
  notice,
}: {
  title: string;
  subtitle: string;
  filter: ComplaintFilter | null;
  onFilter?: (filter: ComplaintFilter | null) => void; // the tabs; none when the filter is fixed
  target?: TargetFilter | null; // who the complaint is against
  onTarget?: (target: TargetFilter | null) => void;
  scope?: "mine" | "all"; // the officer's own complaints, or the whole Level 1 queue
  categoryId?: number | null; // from a dashboard card: only this issue category
  verification?: "failed" | "non_operating" | null; // from a dashboard card: bus verification problems
  onClearFilter?: () => void;
  fixed?: boolean;
  emptyText: string;
  notice?: string;
}) {
  const [typed, setTyped] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [answer, setAnswer] = useState<{ key: string; page?: ComplaintPage; error?: string } | null>(null);
  const key = `${filter}|${target}|${scope}|${categoryId}|${verification}|${search}|${page}`;

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(typed.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [typed]);

  useEffect(() => {
    let current = true;
    void listComplaints({ status: filter, target, scope, categoryId, verification, search, page }).then((result) => {
      if (!current) return;
      setAnswer(result.ok ? { key, page: result.data } : { key, error: result.message });
    });
    return () => {
      current = false;
    };
  }, [filter, target, scope, categoryId, verification, search, page, key]);

  const loading = answer?.key !== key;
  const data = answer?.page;
  const pages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;
  const firstRow = data ? (data.page - 1) * data.pageSize : 0;

  return (
    <Card>
      <CardHeading title={title} subtitle={subtitle} />

      {!fixed && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Complaint against">
          {TARGET_TABS.map((tab) => {
            const count = data?.targetCounts[tab.target ?? "all"];
            return (
              <PillButton
                key={tab.label}
                primary={target === tab.target}
                onClick={() => {
                  setPage(1);
                  onTarget?.(tab.target);
                }}
              >
                {tab.label}
                {count !== undefined && <span className="tabular-nums opacity-80">· {count}</span>}
              </PillButton>
            );
          })}
        </div>
      )}

      {!fixed && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Status">
          {TABS.map((tab) => {
            const count = data?.counts[tab.filter ?? "all"];
            return (
              <PillButton
                key={tab.label}
                primary={filter === tab.filter}
                onClick={() => {
                  setPage(1);
                  onFilter?.(tab.filter);
                }}
              >
                {tab.label}
                {count !== undefined && <span className="tabular-nums opacity-80">· {count}</span>}
              </PillButton>
            );
          })}
        </div>
      )}

      <label className="relative block max-w-[26rem]">
        <span className="sr-only">Search complaints</span>
        <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted">
          <Icon name="search" size={15} />
        </span>
        <input
          type="search"
          className={`${inputClass} !pl-10`}
          placeholder="Search reference, subject, name or bus"
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
        />
      </label>

      {(verification || categoryId) && (
        <div className="flex flex-wrap items-center gap-2">
          <Chip tone="brand">
            {verification === "failed"
              ? "Bus could not be verified"
              : verification === "non_operating"
                ? "Bus did not operate on that date"
                : `Issue category ${data?.rows[0]?.category ?? ""}`.trim()}
          </Chip>
          <PillButton onClick={onClearFilter}>Show all</PillButton>
        </div>
      )}

      {notice && <Note tone="neutral">{notice}</Note>}
      {answer?.error && <Note tone="alert">{answer.error}</Note>}

      {/* relative: a visually hidden label in the last column is absolutely positioned, and without this the
          scroll box does not clip it, so the whole page scrolls sideways */}
      <div className="relative overflow-x-auto">
        <table className="w-full border-separate border-spacing-y-1 text-[0.81rem]">
          <thead>
            <tr>
              <th className={th}>Reference</th>
              <th className={th}>Incident date</th>
              <th className={th}>Bus number</th>
              <th className={th}>Complaint against</th>
              <th className={th}>Accused person</th>
              <th className={th}>Issue category</th>
              <th className={th}>Status</th>
              <th className={th}>Assigned L2 area</th>
              <th className={th}>
                <span className="sr-only">View details</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {data?.rows.map((c) => (
              <tr key={c.id} className="*:bg-[#faf6f7] *:px-2.5 *:py-2.5 *:first:rounded-l-[1.1rem] *:last:rounded-r-[1.1rem]">
                <td className="whitespace-nowrap font-extrabold text-crimson-hover">{c.reference ?? "No reference"}</td>
                <td className="whitespace-nowrap tabular-nums">{day(c.date)}</td>
                <td className="whitespace-nowrap">{c.bus ?? "–"}</td>
                <td className="whitespace-nowrap">{c.target ?? <Chip>Not classified</Chip>}</td>
                <td className="max-w-[12rem] truncate">
                  {c.accused ? (
                    <span title={ACCUSED_NOTE[c.accusedStatus]}>
                      {c.accused}
                      {c.accusedStatus === "verified_duty" && " ✓"}
                    </span>
                  ) : c.targetCode === "bus_service" ? (
                    "–"
                  ) : (
                    <span className="text-muted">Unknown</span>
                  )}
                </td>
                <td className="max-w-[12rem] truncate">{c.category ?? "–"}</td>
                <td>
                  <span className="inline-flex flex-wrap gap-1.5">
                    <Chip tone={STATUS_TONE[c.status]}>{c.status}</Chip>
                    {c.busVerification && c.busVerification !== "verified" && c.busVerification !== "corrected" && (
                      <Chip tone="warn">{VERIFICATION_LABEL[c.busVerification] ?? c.busVerification}</Chip>
                    )}
                    {c.busVerification === "corrected" && <Chip tone="info">Bus corrected</Chip>}
                    {c.synthetic && <Chip tone="info">Simulated</Chip>}
                    {c.possibleDuplicate && <Chip tone="brand">Possible duplicate</Chip>}
                  </span>
                </td>
                <td>{c.area ?? "–"}</td>
                <td>
                  <div className="flex justify-end">
                    <PillLink href={`/l1/new-complaint?id=${c.id}`}>{c.editable ? "Open" : "View details"}</PillLink>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(loading || (data && data.rows.length === 0)) && (
          <p className="py-8 text-center text-[0.86rem] text-muted">
            {loading ? "Loading complaints…" : search ? "No complaint matches your search." : emptyText}
          </p>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className={muted}>
          {data && data.total > 0
            ? `Showing ${firstRow + 1} to ${firstRow + data.rows.length} of ${data.total}`
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