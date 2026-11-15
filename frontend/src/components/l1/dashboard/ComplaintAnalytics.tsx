"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, bigNumber, eyebrow, muted } from "@/components/dashboard/ui";
import { loadAnalytics, type Analytics, type CountRow } from "./api";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function monthLabel(month: string) {
  const [year, number] = month.split("-");
  return number ? `${MONTHS[Number(number) - 1] ?? number} ${year.slice(2)}` : "No date";
}

// Horizontal bars. The widest bar is the largest count in the list.
function Bars({ rows }: { rows: { key: string; label: string; count: number; href?: string }[] }) {
  const widest = Math.max(1, ...rows.map((r) => r.count));
  return (
    <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
      {rows.map((r) => {
        const body = (
          <>
            <span className="min-w-0 flex-1 truncate">{r.label}</span>
            <span className="relative h-2 w-[38%] flex-none overflow-hidden rounded-full bg-[#f1ebed]">
              <span className="absolute inset-y-0 left-0 rounded-full bg-crimson" style={{ width: `${(r.count / widest) * 100}%` }} />
            </span>
            <span className="w-10 flex-none text-right font-extrabold tabular-nums">{r.count}</span>
          </>
        );
        return (
          <li key={r.key}>
            {r.href ? (
              <Link href={r.href} className="focus-ring flex items-center gap-2 rounded-lg py-0.5 text-[0.78rem] hover:bg-[#fbf5f6]">
                {body}
              </Link>
            ) : (
              <div className="flex items-center gap-2 py-0.5 text-[0.78rem]">{body}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

const rowsOf = (rows: CountRow[], link?: (r: CountRow) => string | undefined) =>
  rows.map((r) => ({ key: `${r.id}-${r.name}`, label: r.name, count: r.count, href: link?.(r) }));

// Complaints by issue category, route, district and month, plus the counts that need attention. Every number is a
// PostgreSQL aggregate over this officer's own complaints; the tiles and categories open My Complaints, filtered.
export function ComplaintAnalytics({ className = "", initial }: { className?: string; initial?: Analytics }) {
  const [state, setState] = useState<{ data?: Analytics; error?: string } | null>(initial ? { data: initial } : null);
  const firstShown = useRef(initial !== undefined); // the page came with these already

  useEffect(() => {
    if (firstShown.current) {
      firstShown.current = false;
      return;
    }
    let current = true;
    void loadAnalytics().then((result) => {
      if (current) setState(result.ok ? { data: result.data } : { error: result.message });
    });
    return () => {
      current = false;
    };
  }, []);

  const data = state?.data;
  const tiles: { label: string; value: number | undefined; href?: string }[] = [
    { label: "Duplicate complaints", value: data?.duplicates },
    { label: "Incomplete", value: data?.incomplete, href: "/l1/complaints?status=incomplete" },
    { label: "Failed bus verification", value: data?.failedVerification, href: "/l1/complaints?verification=failed" },
    { label: "Bus did not operate", value: data?.nonOperating, href: "/l1/complaints?verification=non_operating" },
  ];

  return (
    <Card className={className}>
      <CardHeading
        title="Complaint analytics"
        subtitle={data ? `${data.total} complaints you registered` : state?.error ? "Could not load" : "Loading…"}
      />
      {state?.error && <Note tone="alert">{state.error}</Note>}

      <ul className="m-0 grid list-none grid-cols-2 gap-2.5 p-0 min-[1200px]:grid-cols-4">
        {tiles.map((t) => {
          const body = (
            <>
              <span className="text-[0.75rem] font-bold text-muted">{t.label}</span>
              <span className={`${bigNumber} text-[1.7rem]`}>{t.value ?? "–"}</span>
            </>
          );
          const style = "flex flex-col gap-0.5 rounded-[1.25rem] bg-[#faf6f7] px-4 py-3";
          return (
            <li key={t.label}>
              {t.href ? (
                <Link href={t.href} className={`${style} focus-ring transition-shadow hover:shadow-[0_0_0_1.5px_rgba(179,17,47,0.35)]`}>
                  {body}
                </Link>
              ) : (
                <div className={style}>{body}</div>
              )}
            </li>
          );
        })}
      </ul>

      {data && data.total === 0 && <p className={muted}>No complaints yet, so there is nothing to chart.</p>}
      {data && data.total > 0 && (
        <div className="grid gap-5 min-[900px]:grid-cols-2">
          <div className="flex flex-col gap-2">
            <p className={eyebrow}>By issue category</p>
            <Bars rows={rowsOf(data.byCategory, (r) => (r.id ? `/l1/complaints?category_id=${r.id}` : undefined))} />
          </div>
          <div className="flex flex-col gap-2">
            <p className={eyebrow}>By district</p>
            <Bars rows={rowsOf(data.byDistrict)} />
          </div>
          <div className="flex flex-col gap-2">
            <p className={eyebrow}>By route · busiest {data.byRoute.length}</p>
            <Bars rows={rowsOf(data.byRoute)} />
          </div>
          <div className="flex flex-col gap-2">
            <p className={eyebrow}>By month</p>
            <Bars rows={data.byMonth.map((m) => ({ key: m.month, label: monthLabel(m.month), count: m.count }))} />
          </div>
        </div>
      )}
    </Card>
  );
}
