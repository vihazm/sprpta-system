"use client";

import { useEffect, useState } from "react";
import { Field, inputClass } from "@/components/dashboard/controls";
import { Chip, muted } from "@/components/dashboard/ui";
import { searchPeople } from "./api";
import type { PersonRecord, PersonType } from "./types";

const TYPE_LABEL: Record<PersonType, string> = {
  driver: "Driver",
  conductor: "Conductor",
  sprpta_staff: "SPRPTA staff",
  owner: "Owner",
};

const MIN_SEARCH = 2;

// Looks a person up in the records as L1 types (UC-L1-02). Picking a match links the record;
// typing again unlinks it. A person who is not on record cannot be created here: Admin adds them.
export function PersonPicker({
  id,
  label,
  name,
  personId,
  personType,
  placeholder,
  hint,
  onChange,
}: {
  id: string;
  label: string;
  name: string;
  personId: number | null;
  personType?: PersonType;
  placeholder?: string;
  hint?: string;
  onChange: (person: { id: number | null; name: string }) => void;
}) {
  const [found, setFound] = useState<PersonRecord[]>([]);
  const searching = personId === null && name.trim().length >= MIN_SEARCH;

  useEffect(() => {
    if (!searching) return;
    let current = true;
    const timer = setTimeout(async () => {
      const result = await searchPeople(name.trim(), personType);
      if (current && result.ok) setFound(result.data);
    }, 300);
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [name, personType, searching]);

  return (
    <Field label={label} htmlFor={id}>
      <div className="relative">
        <input
          id={id}
          className={`${inputClass} ${personId !== null ? "pr-[7.5rem]" : ""}`}
          value={name}
          placeholder={placeholder}
          autoComplete="off"
          onChange={(e) => onChange({ id: null, name: e.target.value })}
        />
        {personId !== null && (
          <span className="absolute right-2 top-[0.55rem]">
            <Chip tone="ok">Record found</Chip>
          </span>
        )}
      </div>
      {searching && found.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {found.map((person) => (
            <button
              key={person.id}
              type="button"
              onClick={() => onChange({ id: person.id, name: person.name })}
              className="focus-ring cursor-pointer rounded-full border-[1.5px] border-[#E5E7EB] bg-white px-3 py-1 text-[0.75rem] font-bold text-slate-ink transition-colors hover:border-crimson hover:text-crimson"
            >
              {person.name} · {TYPE_LABEL[person.type]}
            </button>
          ))}
        </div>
      )}
      {hint && <p className={muted}>{hint}</p>}
    </Field>
  );
}
