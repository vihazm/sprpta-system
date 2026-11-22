"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/dashboard/ConfirmDialog";
import { CharCount, Field, textareaClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { Card, CardHeading, PillButton, muted } from "@/components/dashboard/ui";
import { notify } from "@/lib/notify";
import { createSolutionDocument } from "../api";
import { ACTION_LABEL, LIMITS, OUTCOME_LABEL } from "../format";
import type { CaseDetail } from "../types";

// The complaint as a starting summary, cut at a word so it fits what the server accepts.
function startingSummary(c: CaseDetail): string {
  const text = [c.subject, c.description].filter(Boolean).join(". ");
  if (text.length <= LIMITS.summary) return text;
  const cut = text.slice(0, LIMITS.summary - 1);
  return `${cut.slice(0, cut.lastIndexOf(" ") > 0 ? cut.lastIndexOf(" ") : cut.length)}…`;
}

// The solution document (UC-L2-05). The case ID and the verdict come from the case and the saved decision; the
// summary starts from the complaint and can be edited; the officer writes what the implementing staff must do.
// Creating it generates the PDF and moves the case to Awaiting implementation, after which nothing can be edited.
export function SolutionDocumentForm({
  c,
  unsaved,
  onChange,
}: {
  c: CaseDetail;
  unsaved: boolean; // the decision above has changes that are not saved yet
  onChange: (c: CaseDetail) => void;
}) {
  const [summary, setSummary] = useState(() => startingSummary(c));
  const [details, setDetails] = useState("");
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const decision = c.decision!;
  const ready = summary.trim() !== "" && details.trim() !== "" && summary.length <= LIMITS.summary;

  async function create() {
    setBusy(true);
    const result = await createSolutionDocument(c.id, { summary: summary.trim(), solutionDetails: details.trim() });
    setBusy(false);
    if (!result.ok) return notify.error("Could not create the solution document", result.message);
    setAsking(false);
    onChange(result.data);
    notify.success("Solution document created", "The case is now awaiting implementation.");
  }

  return (
    <Card>
      <CardHeading title="Solution document" subtitle="A PDF for the implementing staff, handed over outside the system" />
      <div className="grid gap-3 rounded-[1.25rem] bg-[#f7f4f5] p-4 sm:grid-cols-2">
        <div>
          <p className="text-[0.69rem] font-bold text-muted">Case ID</p>
          <p className="mt-0.5 text-[0.81rem] font-extrabold">{c.reference}</p>
        </div>
        <div>
          <p className="text-[0.69rem] font-bold text-muted">Verdict</p>
          <p className="mt-0.5 text-[0.81rem] font-extrabold">
            {ACTION_LABEL[decision.action]} · {OUTCOME_LABEL[decision.outcome]}
          </p>
        </div>
      </div>
      <Field label="Complaint summary" htmlFor="doc-summary">
        <textarea
          id="doc-summary"
          className={`${textareaClass} !h-[5.5rem]`}
          value={summary}
          maxLength={LIMITS.summary}
          onChange={(e) => setSummary(e.target.value)}
        />
        <CharCount value={summary} max={LIMITS.summary} />
      </Field>
      <Field label="Solution to carry out" htmlFor="doc-details">
        <textarea
          id="doc-details"
          className={`${textareaClass} !h-[6.5rem]`}
          value={details}
          maxLength={LIMITS.solution}
          onChange={(e) => setDetails(e.target.value)}
          placeholder="What the implementing staff must do, for example: suspend the driver for 3 days from Monday"
        />
        <CharCount value={details} max={LIMITS.solution} />
      </Field>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#f1ebed] pt-3.5">
        <p className={`${muted} max-w-[28rem]`}>
          {unsaved
            ? "Save your changes to the decision first: the document is made from the saved decision."
            : "The document cannot be edited after it is created, and the decision can no longer be changed."}
        </p>
        <PillButton primary className="!h-11 !px-6" disabled={busy || unsaved || !ready} onClick={() => setAsking(true)}>
          <Icon name="file" size={14} />
          Create solution document
        </PillButton>
      </div>

      {asking && (
        <ConfirmDialog
          title="Create the solution document?"
          confirmLabel="Create PDF"
          busy={busy}
          onConfirm={create}
          onCancel={() => setAsking(false)}
        >
          This generates the PDF for {c.reference} and moves the case to Awaiting implementation. Give the PDF to the
          implementing staff through official channels.
        </ConfirmDialog>
      )}
    </Card>
  );
}
