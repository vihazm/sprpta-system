"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/dashboard/icons";
import { Note } from "@/components/dashboard/Note";
import { OverdueBadge } from "@/components/dashboard/OverdueBadge";
import { SeverityChip } from "@/components/dashboard/severity";
import { Card, Chip, PillLink } from "@/components/dashboard/ui";
import { Skeleton, SkeletonLines } from "@/components/portal/Skeleton";
import { loadCase, solutionDocumentUrl } from "../api";
import { dueText, shortDate } from "../format";
import { isDeciding, StatusTag } from "../status";
import type { CaseDetail } from "../types";

// The case picked in the list, at a glance. Looking at it here changes nothing; "Review and decide" opens the
// full case, which is where a Forwarded case moves to Under review.
export function CaseGlance({ caseId, initial }: { caseId: number | null; initial: CaseDetail | null }) {
  const preloaded = initial?.id === caseId ? initial : null;
  const [answer, setAnswer] = useState<{ detail?: CaseDetail; error?: string } | null>(
    preloaded ? { detail: preloaded } : null,
  );

  useEffect(() => {
    if (caseId === null || preloaded) return;
    let current = true;
    void loadCase(caseId).then((result) => {
      if (current) setAnswer(result.ok ? { detail: result.data } : { error: result.message });
    });
    return () => {
      current = false;
    };
  }, [caseId, preloaded]);

  if (caseId === null) {
    return (
      <Card>
        <p className="text-[0.69rem] font-extrabold uppercase tracking-[0.09em] text-crimson">Case details</p>
        <Note>No case is open in your area right now. Pick one from the list to see it here.</Note>
      </Card>
    );
  }
  if (answer?.error) {
    return (
      <Card>
        <Note tone="alert">{answer.error}</Note>
      </Card>
    );
  }
  const c = answer?.detail;
  if (!c) {
    return (
      <Card className="min-h-[24rem]">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-7 w-2/3" />
        <SkeletonLines count={5} />
      </Card>
    );
  }

  const facts = [
    { label: "Complainant", value: c.isAnonymous ? "Anonymous" : c.complainant ?? "–" },
    { label: "Medium", value: c.medium ?? "–" },
    { label: "Vehicle", value: c.vehicle ?? "–" },
    { label: "Route or stand", value: c.routeStand ?? "–" },
    { label: "Forwarded", value: shortDate(c.forwardedAt) },
    { label: "Contact on record", value: c.hasContact ? "Yes" : "None" },
  ];

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[0.69rem] font-extrabold uppercase tracking-[0.09em] text-crimson">Case details</p>
        <StatusTag status={c.status} />
      </div>

      <div>
        <h3 className="font-display text-[1.6rem] leading-[1.1] tracking-[-0.035em]">{c.reference}</h3>
        <p className="mt-1.5 text-[0.88rem] font-bold leading-[1.35]">{c.subject ?? "No subject"}</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <SeverityChip severity={c.severity} />
          {c.overdue && <OverdueBadge />}
          <Chip>
            <span suppressHydrationWarning>{dueText(c)}</span>
          </Chip>
        </div>
      </div>

      <dl className="m-0 grid grid-cols-2 gap-x-3.5 gap-y-2.5 rounded-[1.25rem] bg-[#f7f4f5] p-3.5">
        {facts.map((f) => (
          <div key={f.label}>
            <dt className="text-[0.69rem] font-bold text-muted">{f.label}</dt>
            <dd className="m-0 mt-0.5 text-[0.78rem] font-extrabold leading-[1.3]">{f.value}</dd>
          </div>
        ))}
      </dl>

      {c.description && (
        <p className="line-clamp-4 text-[0.81rem] leading-[1.55]">
          <b className="font-extrabold">What happened.</b> {c.description}
        </p>
      )}

      {(c.attachments.length > 0 || c.earlier.length > 0) && (
        <p className="flex flex-wrap gap-x-4 gap-y-1 text-[0.75rem] font-bold text-slate-600">
          {c.attachments.length > 0 && (
            <span className="inline-flex items-center gap-1.5">
              <Icon name="attach" size={13} />
              {c.attachments.length} {c.attachments.length === 1 ? "attachment" : "attachments"}
            </span>
          )}
          {c.earlier.length > 0 && (
            <span className="text-crimson-hover">
              {c.earlier.length} earlier {c.earlier.length === 1 ? "complaint" : "complaints"} on record
            </span>
          )}
        </p>
      )}

      <div className="mt-auto flex flex-wrap gap-2 border-t border-[#f1ebed] pt-3.5">
        <PillLink primary href={`/l2/cases/${c.id}`}>
          {isDeciding(c.status) ? "Review and decide" : "Open case"}
        </PillLink>
        {c.solutionDocument && (
          <a
            href={solutionDocumentUrl(c.id)}
            target="_blank"
            rel="noopener"
            className="focus-ring inline-flex h-[2.1rem] items-center gap-[0.45rem] rounded-full border-[1.5px] border-[#E5E7EB] px-[0.95rem] text-[0.78rem] font-bold text-slate-ink transition-colors hover:border-crimson hover:text-crimson"
          >
            <Icon name="download" size={13} />
            Solution document
          </a>
        )}
      </div>
    </Card>
  );
}
