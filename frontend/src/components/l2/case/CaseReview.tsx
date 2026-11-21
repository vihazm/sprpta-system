"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/dashboard/icons";
import { Note } from "@/components/dashboard/Note";
import { OverdueBadge } from "@/components/dashboard/OverdueBadge";
import { SeverityChip } from "@/components/dashboard/severity";
import { Card, PillLink, muted } from "@/components/dashboard/ui";
import { startReview } from "../api";
import { dateTime, dueText } from "../format";
import { isDeciding, StatusTag } from "../status";
import type { CaseDetail } from "../types";
import { CaseHistory, EarlierCases } from "./CaseSidePanels";
import { CaseOutcome } from "./CaseOutcome";
import { ComplaintDetails } from "./ComplaintDetails";
import { DecisionStep } from "./DecisionStep";

// One case (UI-L2-03): its details, what the officer can do at its status, earlier cases and its history.
// Opening a Forwarded case moves it to Under review, which the History panel then shows.
export function CaseReview({ initial }: { initial: CaseDetail }) {
  const [c, setCase] = useState(initial);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current || initial.status !== "forwarded") return;
    started.current = true;
    void startReview(initial.id).then((result) => {
      if (result.ok) setCase(result.data);
      else setReviewError(result.message);
    });
  }, [initial]);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3.5">
          <div className="min-w-0">
            <PillLink href="/l2/cases" className="mb-3">
              <Icon name="prev" size={12} />
              All cases
            </PillLink>
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className="font-display text-[1.9rem] leading-[1.1] tracking-[-0.035em]">{c.reference}</h2>
              <SeverityChip severity={c.severity} />
              <StatusTag status={c.status} />
              {c.overdue && <OverdueBadge />}
            </div>
            <p className="mt-1.5 text-[1rem] font-bold">{c.subject ?? "No subject"}</p>
            <p className={`mt-0.5 ${muted}`}>
              {c.area} area
              {c.forwardedAt && ` · forwarded ${dateTime(c.forwardedAt)}`}
              {c.forwardedBy && ` by ${c.forwardedBy}`}
            </p>
          </div>
          {c.dueKind && (
            <div className={`rounded-2xl px-4 py-2.5 text-right ${c.overdue ? "bg-red-50" : "bg-crimson/10"}`}>
              <p suppressHydrationWarning className={`text-[0.84rem] font-extrabold ${c.overdue ? "text-red-800" : "text-crimson-deep"}`}>
                {dueText(c)}
              </p>
              <p className="text-[0.75rem] text-crimson-hover">{c.dueKind === "decide" ? "Decide-by target" : "Close-by target"}</p>
            </div>
          )}
        </div>
        {reviewError && <Note tone="alert">The case could not be moved to Under review: {reviewError}</Note>}
      </Card>

      <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
        <div className="flex min-w-0 flex-col gap-4 min-[1200px]:col-span-8">
          <ComplaintDetails c={c} />
          {isDeciding(c.status) ? <DecisionStep c={c} onChange={setCase} /> : <CaseOutcome c={c} />}
        </div>
        <div className="flex min-w-0 flex-col gap-4 min-[1200px]:col-span-4">
          <EarlierCases c={c} />
          <CaseHistory history={c.history} />
        </div>
      </div>
    </div>
  );
}
