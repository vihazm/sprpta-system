"use client";

import { useState } from "react";

export type Choice = { value: string; dot?: string }; // dot is an optional colour

// A row of pill buttons that works like radio buttons, or like checkboxes with `multiple`.
// "dark" is the filled look used for severity.
export function ChoiceGroup({
  label,
  choices,
  defaultValue,
  multiple = false,
  look = "soft",
  onChange,
}: {
  label: string;
  choices: Choice[];
  defaultValue: string | string[];
  multiple?: boolean;
  look?: "soft" | "dark";
  onChange?: (chosen: string[]) => void;
}) {
  const [chosen, setChosen] = useState([defaultValue].flat());

  function pick(value: string) {
    const next = !multiple
      ? [value]
      : chosen.includes(value)
        ? chosen.filter((v) => v !== value)
        : [...chosen, value];
    setChosen(next);
    onChange?.(next);
  }

  const on = look === "dark" ? "border-ink bg-ink text-white" : "border-crimson bg-crimson/10 text-crimson-deep";

  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-2">
      {choices.map((choice) => (
        <button
          key={choice.value}
          type="button"
          aria-pressed={chosen.includes(choice.value)}
          onClick={() => pick(choice.value)}
          className={`focus-ring inline-flex cursor-pointer items-center gap-[0.45rem] rounded-full border-[1.5px] px-[0.95rem] py-2 text-[0.78rem] font-bold transition-colors ${
            chosen.includes(choice.value) ? on : "border-[#E5E7EB] bg-white text-slate-ink hover:border-crimson"
          }`}
        >
          {choice.dot && (
            <span aria-hidden="true" className="size-2 rounded-full" style={{ background: choice.dot }} />
          )}
          {choice.value}
        </button>
      ))}
    </div>
  );
}
