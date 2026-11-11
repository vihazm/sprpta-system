"use client";

import { useState } from "react";
import { ChoiceGroup } from "@/components/dashboard/ChoiceGroup";
import { Field, inputClass, textareaClass } from "@/components/dashboard/controls";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, PillButton } from "@/components/dashboard/ui";

const KINDS = [{ value: "Improvement suggestion" }, { value: "Commendation" }];

// A suggestion to improve the service, or praise for a person (UC-L1-11).
export function RecommendationForm({ className = "" }: { className?: string }) {
  const [commendation, setCommendation] = useState(true);

  return (
    <Card className={className}>
      <CardHeading
        title="Log a recommendation"
        subtitle="A suggestion to improve the service, or praise for a person"
      />
      <ChoiceGroup
        label="Kind of recommendation"
        choices={KINDS}
        defaultValue="Commendation"
        onChange={([kind]) => setCommendation(kind === "Commendation")}
      />
      {commendation && (
        <Field label="Person commended" htmlFor="rec-person">
          <input id="rec-person" className={inputClass} defaultValue="Conductor, bus NB-4521" />
        </Field>
      )}
      <Field label="Details" htmlFor="rec-details">
        <textarea
          id="rec-details"
          className={textareaClass}
          defaultValue="A passenger thanked the conductor for helping a wheelchair user board at Matara stand."
        />
      </Field>
      <PillButton primary className="self-start">
        Save recommendation
      </PillButton>
      <Note className="mt-auto">
        After you save, only Level 2 and Level 3 can see it. It will not appear here again.
      </Note>
    </Card>
  );
}
