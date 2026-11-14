"use client";

import { useState } from "react";
import { ChoiceGroup } from "@/components/dashboard/ChoiceGroup";
import { Field, inputClass } from "@/components/dashboard/controls";
import { PillButton, muted } from "@/components/dashboard/ui";
import type { RejectionType } from "./types";

const REASONS: { value: string; type: RejectionType }[] = [
  { value: "Invalid", type: "invalid" },
  { value: "Spam", type: "spam" },
  { value: "Out of jurisdiction", type: "out_of_jurisdiction" },
  { value: "Duplicate of an earlier case", type: "duplicate" },
];

// Rejecting a complaint that cannot be forwarded (UC-L1-07). The reason is mandatory, and a
// duplicate must name the earlier case. Rejected is final.
export function RejectPanel({
  suggestedEarlier,
  busy,
  onReject,
}: {
  suggestedEarlier: string; // the case L1 marked as the one this duplicates, if any
  busy: boolean;
  onReject: (rejection: { type: RejectionType; reason: string; earlierReference: string }) => void;
}) {
  const [type, setType] = useState<RejectionType>("invalid");
  const [reason, setReason] = useState("");
  const [earlier, setEarlier] = useState<string | null>(null); // null until L1 types in the box

  const duplicate = type === "duplicate";

  return (
    <div className="flex flex-col gap-3 rounded-[1.25rem] border-[1.5px] border-dashed border-[#e8c9cf] p-4">
      <p className="text-[0.81rem] font-extrabold text-crimson-hover">Cannot be forwarded? Reject with a reason</p>
      <ChoiceGroup
        label="Reason for rejecting"
        choices={REASONS}
        defaultValue="Invalid"
        onChange={([value]) => setType(REASONS.find((r) => r.value === value)?.type ?? "invalid")}
      />
      <div className="grid items-end gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto]">
        <Field label="Reason (required)" htmlFor="r-why">
          <input
            id="r-why"
            className={inputClass}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="For example: same incident as the earlier case"
          />
        </Field>
        <Field label="Earlier case" htmlFor="r-ref">
          <input
            id="r-ref"
            className={inputClass}
            value={earlier ?? suggestedEarlier}
            onChange={(e) => setEarlier(e.target.value)}
            disabled={!duplicate}
            placeholder={duplicate ? "Reference number" : "Duplicates only"}
          />
        </Field>
        <PillButton
          className="!h-11 !border-red-200 !text-red-800"
          disabled={busy}
          onClick={() => onReject({ type, reason, earlierReference: earlier ?? suggestedEarlier })}
        >
          Reject case
        </PillButton>
      </div>
      <p className={muted}>Rejected is final. Level 3 cannot reinstate a rejected case.</p>
    </div>
  );
}
