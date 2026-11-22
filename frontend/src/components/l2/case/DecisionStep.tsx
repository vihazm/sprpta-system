"use client";

import { useState } from "react";
import { ChoiceGroup } from "@/components/dashboard/ChoiceGroup";
import { ConfirmDialog } from "@/components/dashboard/ConfirmDialog";
import { CharCount, Field, textareaClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { Card, CardHeading, PillButton, muted } from "@/components/dashboard/ui";
import { notify } from "@/lib/notify";
import { escalateCase, recordDecision } from "../api";
import { ACTION_LABEL, LIMITS, OUTCOME_LABEL } from "../format";
import type { CaseDetail, DecisionAction, DecisionOutcome } from "../types";
import { SolutionDocumentForm } from "./SolutionDocumentForm";

const ACTIONS = Object.entries(ACTION_LABEL).map(([key, value]) => ({ key: key as DecisionAction, value }));
const OUTCOMES = Object.entries(OUTCOME_LABEL).map(([key, value]) => ({ key: key as DecisionOutcome, value }));

// Deciding the case (UC-L2-04), then the solution document (UC-L2-05), or escalating it (UC-L2-07) at any point
// before the document exists. The officer decides on their own: the AI suggestion is added once the AI model
// exists. Nothing is chosen in advance.
export function DecisionStep({ c, onChange }: { c: CaseDetail; onChange: (c: CaseDetail) => void }) {
  const [action, setAction] = useState<DecisionAction | null>(c.decision?.action ?? null);
  const [outcome, setOutcome] = useState<DecisionOutcome | null>(c.decision?.outcome ?? null);
  const [reasoning, setReasoning] = useState(c.decision?.reasoning ?? "");
  const [busy, setBusy] = useState(false);
  const [escalating, setEscalating] = useState(false);

  const complete = action !== null && outcome !== null && reasoning.trim() !== "";
  const unchanged =
    c.decision !== null &&
    action === c.decision.action &&
    outcome === c.decision.outcome &&
    reasoning.trim() === c.decision.reasoning;
  const unsaved = c.decision !== null && !unchanged; // the solution document is made from the saved decision only

  async function save() {
    if (!action || !outcome) return;
    setBusy(true);
    const result = await recordDecision(c.id, { action, outcome, reasoning: reasoning.trim() });
    setBusy(false);
    if (!result.ok) return notify.error("Could not record the decision", result.message);
    onChange(result.data);
    notify.success(c.decision ? "Decision updated" : "Decision recorded", "Next, create the solution document.");
  }

  async function escalate(reason: string) {
    setBusy(true);
    const result = await escalateCase(c.id, reason);
    setBusy(false);
    if (!result.ok) return notify.error("Could not escalate the case", result.message);
    setEscalating(false);
    onChange(result.data);
    notify.success("Escalated to Level 3", `${c.reference} has left your action list.`);
  }

  return (
    <>
      <Card>
        <CardHeading
          title="Your decision"
          subtitle="All fields are required. You can change the decision, or still escalate, until the solution document is created."
        />
        <Field label="Action">
          <ChoiceGroup
            label="Action"
            choices={ACTIONS}
            defaultValue={action ? ACTION_LABEL[action] : []}
            onChange={([value]) => setAction(ACTIONS.find((a) => a.value === value)?.key ?? null)}
          />
        </Field>
        <Field label="Outcome">
          <ChoiceGroup
            label="Outcome"
            choices={OUTCOMES}
            defaultValue={outcome ? OUTCOME_LABEL[outcome] : []}
            onChange={([value]) => setOutcome(OUTCOMES.find((o) => o.value === value)?.key ?? null)}
          />
        </Field>
        <Field label="Reasoning" htmlFor="decision-reasoning">
          <textarea
            id="decision-reasoning"
            className={`${textareaClass} !h-[6.5rem]`}
            value={reasoning}
            maxLength={LIMITS.reasoning}
            onChange={(e) => setReasoning(e.target.value)}
            placeholder="Why this action, given the evidence and any earlier cases"
          />
          <CharCount value={reasoning} max={LIMITS.reasoning} />
        </Field>
        <p className={muted}>The outcome later counts towards the accused person&apos;s rating.</p>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#f1ebed] pt-3.5">
          <PillButton className="!border-crimson !text-crimson-hover" disabled={busy} onClick={() => setEscalating(true)}>
            <Icon name="up" size={14} />
            Escalate to Level 3
          </PillButton>
          <div className="flex flex-wrap items-center gap-3">
            {unsaved && <span className={muted}>You have unsaved changes.</span>}
            <PillButton primary className="!h-11 !px-6" disabled={busy || !complete || unchanged} onClick={save}>
              <Icon name="check" size={14} />
              {c.decision ? "Save changes" : "Record decision"}
            </PillButton>
          </div>
        </div>
      </Card>

      {c.decision && <SolutionDocumentForm c={c} unsaved={unsaved} onChange={onChange} />}

      {escalating && (
        <ConfirmDialog
          title={`Escalate ${c.reference} to Level 3?`}
          confirmLabel="Escalate"
          reasonLabel="Reason (required)"
          reasonMax={LIMITS.escalation}
          busy={busy}
          onConfirm={escalate}
          onCancel={() => setEscalating(false)}
        >
          Escalate only when the case cannot be resolved within your area. The status becomes Escalated and the case
          leaves your action list. It does not come back.
          {c.decision && " Your recorded decision is withdrawn, since Level 3 makes its own. The History keeps it."}
        </ConfirmDialog>
      )}
    </>
  );
}
