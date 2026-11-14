"use client";

import { ChoiceGroup } from "@/components/dashboard/ChoiceGroup";
import type { DuplicateCandidate, DuplicateChoice } from "./types";

// Possible duplicates of the complaint being entered (UC-L1-03). Nothing is merged or deleted;
// L1 records a choice for each one.
export function DuplicatePanel({
  candidates,
  onChoose,
}: {
  candidates: DuplicateCandidate[];
  onChoose: (candidateId: number, choice: DuplicateChoice) => void;
}) {
  if (candidates.length === 0) return null;

  return (
    <div className="flex flex-col gap-2.5 rounded-[1.25rem] bg-amber-50 px-4 py-3.5">
      {candidates.map((candidate) => {
        const choices: { value: string; choice: DuplicateChoice }[] = [
          { value: "Not a duplicate", choice: "not_duplicate" },
          { value: `Duplicate of ${candidate.reference}`, choice: "duplicate_of" },
          { value: "Related, link them", choice: "related" },
        ];
        return (
          <div key={candidate.id} className="flex flex-col gap-2.5">
            <p className="text-[0.81rem] font-extrabold text-amber-900">
              Possible duplicate: {candidate.reference}, {candidate.subject ?? "no subject"}, {candidate.match}% match
            </p>
            <ChoiceGroup
              label={`Duplicate check for ${candidate.reference}`}
              choices={choices}
              defaultValue={choices.find((c) => c.choice === candidate.choice)?.value ?? ""}
              onChange={([value]) => {
                const picked = choices.find((c) => c.value === value);
                if (picked) onChoose(candidate.id, picked.choice);
              }}
            />
          </div>
        );
      })}
      <p className="text-[0.75rem] text-amber-900">
        Nothing is merged or deleted. A duplicate is rejected with a reason that names the earlier case.
      </p>
    </div>
  );
}
