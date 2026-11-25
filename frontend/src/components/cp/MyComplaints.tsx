"use client";

import Link from "next/link";
import { useState } from "react";
import { Card, Chip, eyebrow, muted } from "@/components/dashboard/ui";
import { StatusTimeline } from "./StatusTimeline";
import { StepBar } from "./StepBar";
import { formatDate, referenceText, statusTone, whatNext } from "./status";
import type { PortalComplaint } from "./types";

/** My complaints (UI-CP-03 and UI-CP-05): pick a complaint, see which of the four steps it is at. Read only. */
export function MyComplaints({ complaints, selectedId }: { complaints: PortalComplaint[]; selectedId: number | null }) {
  const [picked, setPicked] = useState<number | null>(selectedId);
  const current = complaints.find((c) => c.id === picked) ?? complaints[0];

  if (!current) return <Empty />;
  const next = whatNext(current);

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className={eyebrow}>My complaints</p>
        <h1 className="mt-1.5 font-display text-[2.3rem] leading-[1.08] tracking-[-0.035em] max-[599px]:text-[1.8rem]">
          Follow each step
        </h1>
      </div>

      <div className="flex flex-wrap items-start gap-5">
        <Card className="flex-[1_1_20rem] !gap-2.5">
          <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
            {complaints.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  aria-pressed={c.id === current.id}
                  onClick={() => setPicked(c.id)}
                  className={`focus-ring flex w-full cursor-pointer flex-col gap-2.5 rounded-[1.1rem] border-0 p-3.5 text-left transition-shadow ${
                    c.id === current.id ? "bg-white shadow-[0_0_0_2px_#b3112f]" : "bg-[#f7f4f5] hover:bg-[#f0eced]"
                  }`}
                >
                  <span className="text-[0.9rem] font-bold text-ink">{c.subject}</span>
                  <span className="flex">
                    <Chip tone={statusTone(c)}>{c.statusLabel}</Chip>
                  </span>
                  <StepBar complaint={c} />
                  <span className={muted}>
                    {referenceText(c)} · {formatDate(c.submittedAt)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="flex-[1.7_1_26rem] !gap-6 !p-[1.9rem]">
          <div className="flex flex-wrap items-start justify-between gap-2.5">
            <div className="min-w-0 flex-[1_1_16rem]">
              <p className={eyebrow}>{referenceText(current)}</p>
              <h2 className="mt-1.5 font-display text-[1.6rem] leading-[1.2]">{current.subject}</h2>
            </div>
            <Chip tone={statusTone(current)} large>
              {current.statusLabel}
            </Chip>
          </div>

          <StatusTimeline complaint={current} />

          <div className="rounded-[1.1rem] bg-[#f7f4f5] px-[1.1rem] py-[0.95rem]">
            <p className="text-[0.88rem] font-extrabold">{next.title}</p>
            <p className={`mt-1 ${muted}`}>{next.detail}</p>
          </div>

          <dl className="m-0 grid grid-cols-[repeat(auto-fit,minmax(9.5rem,1fr))] gap-4">
            <Detail label="Submitted" value={formatDate(current.submittedAt)} />
            <Detail label="Incident date" value={formatDate(current.complaintDate)} />
            <Detail label="Complaint about" value={current.targetName} />
            <Detail label="Category" value={current.categoryName} />
            <Detail label="Vehicle" value={current.vehicleNumber} />
            <Detail label="Area" value={current.areaName} />
            <Detail label="Route or stand" value={current.routeStandName} />
          </dl>
          {current.description && (
            <div>
              <p className={eyebrow}>What you wrote</p>
              <p className="mt-1.5 whitespace-pre-wrap text-[0.88rem] leading-[1.55] text-slate-ink">{current.description}</p>
            </div>
          )}
          <p className={`border-t border-[#efe9eb] pt-3 ${muted}`}>
            Updates about this case reach you by SMS or email. Staff notes and internal steps are not shown here.
          </p>
        </Card>
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div>
      <dt className={eyebrow}>{label}</dt>
      <dd className="m-0 mt-1 text-[0.88rem] font-bold">{value}</dd>
    </div>
  );
}

function Empty() {
  return (
    <Card className="items-start gap-3 !p-8">
      <p className={eyebrow}>My complaints</p>
      <h1 className="font-display text-[1.7rem] leading-[1.15]">You have not lodged a complaint yet</h1>
      <p className="max-w-[30rem] text-[0.9rem] leading-[1.5] text-muted">
        Once you submit one, it appears here and you can follow it step by step.
      </p>
      <Link
        href="/cp/new-complaint"
        className="focus-ring mt-1 inline-flex h-12 items-center rounded-[0.95rem] bg-crimson px-6 text-[0.9rem] font-extrabold text-white transition-colors hover:bg-crimson-hover"
      >
        Lodge your first complaint
      </Link>
    </Card>
  );
}
