"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { ConfirmDialog } from "@/components/dashboard/ConfirmDialog";
import { Card, Chip, PillButton, eyebrow, muted } from "@/components/dashboard/ui";
import { notify } from "@/lib/notify";
import { deleteComplaint } from "./api";
import { AttachmentGallery } from "./AttachmentGallery";
import { StatusTimeline } from "./StatusTimeline";
import { StepBar } from "./StepBar";
import { formatDate, referenceText, statusTone, whatNext } from "./status";
import type { PortalAttachment, PortalComplaint } from "./types";

/**
 * My complaints (UI-CP-03 and UI-CP-05): pick a complaint, see which of the four steps it is at and the files it has.
 * While SPRPTA has not started on a complaint, its files can be changed and the whole complaint can be deleted.
 */
export function MyComplaints({ complaints: initial, selectedId }: { complaints: PortalComplaint[]; selectedId: number | null }) {
  const [complaints, setComplaints] = useState(initial);
  const [picked, setPicked] = useState<number | null>(selectedId);
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const current = complaints.find((c) => c.id === picked) ?? complaints[0];
  const inProgress = complaints.filter((c) => c.outcome === "open").length;

  function setFiles(id: number, attachments: PortalAttachment[]) {
    setComplaints((list) => list.map((c) => (c.id === id ? { ...c, attachments } : c)));
  }

  async function remove() {
    if (!current) return;
    setBusy(true);
    const result = await deleteComplaint(current.id);
    setBusy(false);
    setAsking(false);
    if (!result.ok) return notify.error("Complaint not deleted", result.message);
    notify.success("Complaint deleted", "It is no longer in your list.");
    setPicked(null);
    setComplaints((list) => list.filter((c) => c.id !== current.id));
  }

  if (!current) return <Empty />;
  const next = whatNext(current);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className={eyebrow}>My complaints</p>
          <h1 className="mt-1.5 font-display text-[2.3rem] leading-[1.08] tracking-[-0.035em] max-[599px]:text-[1.8rem]">
            Follow each step
          </h1>
          <p className={`mt-2 ${muted}`}>
            {complaints.length} {complaints.length === 1 ? "complaint" : "complaints"} · {inProgress} in progress
          </p>
        </div>
        <Link
          href="/cp/new-complaint"
          className="focus-ring inline-flex h-11 items-center rounded-[0.95rem] bg-crimson px-5 text-[0.88rem] font-extrabold text-white transition-colors hover:bg-crimson-hover"
        >
          New complaint
        </Link>
      </div>

      <div className="flex flex-wrap items-start gap-5">
        <Card className="flex-[1_1_20rem] !gap-3">
          <h2 className="font-display text-[1.15rem] leading-[1.2]">Your complaints</h2>
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
                    {c.attachments.length > 0 && ` · ${c.attachments.length} ${c.attachments.length === 1 ? "file" : "files"}`}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="flex-[1.7_1_26rem] !gap-0 !p-0">
          <div className="flex flex-wrap items-start justify-between gap-2.5 px-[1.9rem] pb-5 pt-[1.9rem]">
            <div className="min-w-0 flex-[1_1_16rem]">
              <p className={eyebrow}>{referenceText(current)}</p>
              <h2 className="mt-1.5 font-display text-[1.6rem] leading-[1.2]">{current.subject}</h2>
            </div>
            <Chip tone={statusTone(current)} large>
              {current.statusLabel}
            </Chip>
          </div>

          <Block title="Progress">
            <StatusTimeline complaint={current} />
            <div className="rounded-[1.1rem] bg-[#f7f4f5] px-[1.1rem] py-[0.95rem]">
              <p className="text-[0.88rem] font-extrabold">{next.title}</p>
              <p className={`mt-1 ${muted}`}>{next.detail}</p>
            </div>
          </Block>

          <Block title="Details">
            <dl className="m-0 grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] gap-x-5 gap-y-4">
              <Detail label="Submitted" value={formatDate(current.submittedAt)} />
              <Detail label="Incident date" value={formatDate(current.complaintDate)} />
              <Detail label="Complaint about" value={current.targetName} />
              <Detail label="Category" value={current.categoryName} />
              <Detail label="Vehicle" value={current.vehicleNumber} />
              <Detail label="Area" value={current.areaName} />
              <Detail label="Route or stand" value={current.routeStandName} />
            </dl>
          </Block>

          {current.description && (
            <Block title="What you wrote">
              <p className="m-0 whitespace-pre-wrap text-[0.9rem] leading-[1.6] text-slate-ink">{current.description}</p>
            </Block>
          )}

          <Block title="Evidence">
            <AttachmentGallery
              key={current.id}
              complaintId={current.id}
              attachments={current.attachments}
              editable={current.canDelete}
              onChange={(next) => setFiles(current.id, next)}
            />
          </Block>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#efe9eb] px-[1.9rem] py-4">
            <p className={`m-0 max-w-[26rem] ${muted}`}>
              Updates about this case reach you by SMS or email. Staff notes and internal steps are not shown here.
            </p>
            {current.canDelete && <PillButton onClick={() => setAsking(true)}>Delete complaint</PillButton>}
          </div>
        </Card>
      </div>

      {asking && (
        <ConfirmDialog
          title="Delete this complaint?"
          confirmLabel="Delete"
          busy={busy}
          onConfirm={() => void remove()}
          onCancel={() => setAsking(false)}
        >
          SPRPTA has not started on “{current.subject}” yet, so you can still delete it. It will disappear from your
          list and SPRPTA staff will not see it. SPRPTA keeps a record that it was submitted and deleted.
        </ConfirmDialog>
      )}
    </div>
  );
}

/** One titled section of the complaint card, set off by a line. */
function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-4 border-t border-[#efe9eb] px-[1.9rem] py-5">
      <h3 className="m-0 text-[0.69rem] font-bold uppercase tracking-[0.09em] text-muted">{title}</h3>
      {children}
    </section>
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
