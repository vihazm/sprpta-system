"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { inputClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, Chip, PillButton, muted } from "@/components/dashboard/ui";
import { listRecommendations } from "../api";
import { RECOMMENDATION_STATUS_LABEL, RECOMMENDATION_TONE, RECOMMENDATION_TYPE_LABEL, shortDate } from "../format";
import type { RecommendationPage, RecommendationStatus, RecommendationType } from "../types";

const TYPES: { type: RecommendationType | null; label: string }[] = [
  { type: null, label: "All types" },
  { type: "improvement", label: "Improvement suggestions" },
  { type: "commendation", label: "Commendations" },
];
const STATUSES = Object.keys(RECOMMENDATION_STATUS_LABEL) as RecommendationStatus[];

// The recommendation register (UI-L2-09): search, filter by type and status, open one. Read-only for Level 2.
export function RecommendationsList({ initial }: { initial?: RecommendationPage }) {
  const [typed, setTyped] = useState("");
  const [search, setSearch] = useState("");
  const [type, setType] = useState<RecommendationType | null>(null);
  const [status, setStatus] = useState<RecommendationStatus | null>(null);
  const [page, setPage] = useState(1);
  const key = `${type}|${status}|${search}|${page}`;
  const [answer, setAnswer] = useState<{ key: string; page?: RecommendationPage; error?: string } | null>(
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
    void listRecommendations({ type, status, search, page }).then((result) => {
      if (current) setAnswer(result.ok ? { key, page: result.data } : { key, error: result.message });
    });
    return () => {
      current = false;
    };
  }, [type, status, search, page, key]);

  const loading = answer?.key !== key;
  const data = answer?.page;
  const pages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  return (
    <Card>
      <CardHeading
        title="Recommendations"
        subtitle="Improvement suggestions and commendations entered by Level 1. Only Level 3 changes their status."
      />
      <div className="flex flex-wrap gap-2" role="group" aria-label="Type">
        {TYPES.map((t) => (
          <PillButton
            key={t.label}
            primary={type === t.type}
            onClick={() => {
              setType(t.type);
              setPage(1);
            }}
          >
            {t.label}
          </PillButton>
        ))}
      </div>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Status">
        {[null, ...STATUSES].map((s) => (
          <PillButton
            key={s ?? "all"}
            primary={status === s}
            onClick={() => {
              setStatus(s);
              setPage(1);
            }}
          >
            {s ? RECOMMENDATION_STATUS_LABEL[s] : "Any status"}
            {data && <span className="tabular-nums opacity-80">· {data.counts[s ?? "all"] ?? 0}</span>}
          </PillButton>
        ))}
      </div>
      <label className="relative block max-w-[26rem]">
        <span className="sr-only">Search recommendations</span>
        <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted">
          <Icon name="search" size={15} />
        </span>
        <input
          type="search"
          className={`${inputClass} !pl-10`}
          placeholder="Search title or details"
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
        />
      </label>

      {answer?.error && <Note tone="alert">{answer.error}</Note>}

      <ul className={`m-0 flex list-none flex-col gap-1 p-0 transition-opacity ${loading ? "opacity-60" : ""}`}>
        {data?.items.map((r) => (
          <li key={r.id}>
            <Link
              href={`/l2/recommendations/${r.id}`}
              className="focus-ring flex flex-wrap items-center gap-3 rounded-[1.1rem] bg-[#faf6f7] px-3.5 py-3 transition-colors hover:bg-[#f3ecee]"
            >
              <span className="flex size-9 flex-none items-center justify-center rounded-xl bg-crimson/10 text-crimson-hover">
                <Icon name="bulb" size={17} />
              </span>
              <span className="min-w-[12rem] flex-1">
                <span className="block text-[0.84rem] font-extrabold">{r.title}</span>
                <span className={muted}>
                  {RECOMMENDATION_TYPE_LABEL[r.type]} · received {shortDate(r.receivedDate ?? r.createdAt)}
                </span>
              </span>
              <Chip tone={RECOMMENDATION_TONE[r.status]}>{RECOMMENDATION_STATUS_LABEL[r.status]}</Chip>
            </Link>
          </li>
        ))}
      </ul>
      {(loading || data?.items.length === 0) && (
        <p className="py-8 text-center text-[0.86rem] text-muted">
          {loading ? "Loading recommendations…" : "No recommendations match."}
        </p>
      )}

      {data && pages > 1 && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className={muted}>
            Page {data.page} of {pages} · {data.total} in total
          </p>
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
        </div>
      )}
    </Card>
  );
}
