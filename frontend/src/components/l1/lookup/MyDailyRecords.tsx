"use client";

import { useEffect, useRef, useState } from "react";
import { inputClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, Chip, PillButton, muted } from "@/components/dashboard/ui";
import { formatDay } from "./format";
import { listDailyRecords, type DailyRecordPage } from "./records-api";

const th = "px-2.5 py-1 text-left text-[0.69rem] font-bold uppercase tracking-[0.07em] text-muted";

// The daily records this officer entered, newest first, with what stage each is at. Open one to view or edit it
// while it is still pending. `refresh` changes whenever a record is saved, so the list reloads.
// `initial` is the first page, loaded on the server together with the page.
export function MyDailyRecords({
  refresh,
  onOpen,
  initial,
}: {
  refresh: number;
  onOpen: (id: number) => void;
  initial?: DailyRecordPage;
}) {
  const [typed, setTyped] = useState("");
  const [search, setSearch] = useState("");
  const [date, setDate] = useState("");
  const [page, setPage] = useState(1);
  const key = `${search}|${date}|${page}|${refresh}`;
  const [answer, setAnswer] = useState<{ key: string; page?: DailyRecordPage; error?: string } | null>(
    initial ? { key, page: initial } : null,
  );
  const firstPageShown = useRef(initial !== undefined);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(typed.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [typed]);

  useEffect(() => {
    if (firstPageShown.current) {
      firstPageShown.current = false;
      return;
    }
    let current = true;
    void listDailyRecords({ date, search, page }).then((result) => {
      if (current) setAnswer(result.ok ? { key, page: result.data } : { key, error: result.message });
    });
    return () => {
      current = false;
    };
  }, [date, search, page, key]);

  const loading = answer?.key !== key;
  const data = answer?.page;
  const pages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  return (
    <Card>
      <CardHeading
        title="My Daily Bus Records"
        subtitle="The records you entered. A pending record is not shown in the lookup until Admin publishes it."
      />
      <div className="flex flex-wrap gap-3">
        <label className="relative block max-w-[18rem] flex-1">
          <span className="sr-only">Search by bus number</span>
          <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted">
            <Icon name="search" size={15} />
          </span>
          <input type="search" className={`${inputClass} !pl-10`} placeholder="Search by bus number" value={typed}
            onChange={(e) => setTyped(e.target.value)} />
        </label>
        <label className="block">
          <span className="sr-only">Operation date</span>
          <input type="date" className={inputClass} value={date} onChange={(e) => { setDate(e.target.value); setPage(1); }} />
        </label>
      </div>
      {answer?.error && <Note tone="alert">{answer.error}</Note>}
      <div className="relative overflow-x-auto">
        <table className="w-full border-separate border-spacing-y-1 text-[0.81rem]">
          <thead>
            <tr>
              <th className={th}>Date</th>
              <th className={th}>Bus</th>
              <th className={th}>Route</th>
              <th className={th}>Start</th>
              <th className={th}>Driver</th>
              <th className={th}>Conductor</th>
              <th className={th}>Status</th>
              <th className={th}><span className="sr-only">Open</span></th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((r) => (
              <tr key={r.id} className="*:bg-[#faf6f7] *:px-2.5 *:py-2.5 *:first:rounded-l-[1.1rem] *:last:rounded-r-[1.1rem]">
                <td className="whitespace-nowrap tabular-nums">{formatDay(r.fields.date)}</td>
                <td className="whitespace-nowrap font-extrabold text-crimson-hover">{r.fields.busNumber}</td>
                <td className="max-w-[14rem] truncate">{r.route}</td>
                <td className="tabular-nums">{r.fields.departure}</td>
                <td>{r.fields.driver.name || "–"}</td>
                <td>{r.fields.conductor.name || "–"}</td>
                <td><Chip tone={r.status === "published" ? "ok" : "warn"}>{r.statusLabel}</Chip></td>
                <td>
                  <div className="flex justify-end">
                    <PillButton onClick={() => onOpen(r.id)}>{r.editable ? "Open" : "View"}</PillButton>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(loading || (data && data.items.length === 0)) && (
          <p className="py-8 text-center text-[0.86rem] text-muted">
            {loading ? "Loading your records…" : search || date ? "No record matches your search." : "You have not entered any daily bus records yet."}
          </p>
        )}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className={muted}>{data && data.total > 0 ? `${data.total} record${data.total === 1 ? "" : "s"}` : "Nothing to show"}</p>
        {data && pages > 1 && (
          <div className="flex gap-2">
            <PillButton disabled={data.page === 1} onClick={() => setPage(data.page - 1)}>
              <Icon name="prev" size={12} />Previous
            </PillButton>
            <PillButton disabled={data.page === pages} onClick={() => setPage(data.page + 1)}>
              Next<Icon name="next" size={12} />
            </PillButton>
          </div>
        )}
      </div>
    </Card>
  );
}
