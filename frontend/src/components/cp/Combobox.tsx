"use client";

import { useId, useState, type ReactNode } from "react";
import { inputClass } from "@/components/dashboard/controls";

export type Choice = { key: string; label: string; hint?: string };

/** The part of a label that matches what was typed is shown in bold. */
function Highlight({ label, typed }: { label: string; typed: string }) {
  const at = typed ? label.toLowerCase().indexOf(typed.toLowerCase()) : -1;
  if (at < 0) return <>{label}</>;
  return (
    <>
      {label.slice(0, at)}
      <b className="font-extrabold text-crimson">{label.slice(at, at + typed.length)}</b>
      {label.slice(at + typed.length)}
    </>
  );
}

/**
 * A text box that offers matching choices as you type: arrow keys and Enter, the mouse, or just keep typing.
 * The parent decides what the choices are (a filtered list, or what the server found) and what picking one does.
 * The box itself is plain text; `onType` hears every keystroke.
 */
export function Combobox({
  id,
  value,
  onType,
  choices,
  onPick,
  placeholder,
  invalid = false,
  describedBy,
  maxLength,
  emptyNote,
  onBlurText,
}: {
  id: string;
  value: string;
  onType: (text: string) => void;
  choices: Choice[];
  onPick: (choice: Choice) => void;
  placeholder?: string;
  invalid?: boolean;
  describedBy?: string;
  maxLength?: number;
  /** Shown when something was typed but nothing matches. */
  emptyNote?: ReactNode;
  /** Called when the box loses focus, with the text in it. */
  onBlurText?: (text: string) => void;
}) {
  const listId = useId();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const shown = open && value.trim() !== "";
  const current = Math.min(active, Math.max(choices.length - 1, 0));

  function pick(choice: Choice) {
    onPick(choice);
    setOpen(false);
  }

  return (
    <div className="relative">
      <input
        id={id}
        className={inputClass}
        role="combobox"
        aria-expanded={shown && choices.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={shown && choices.length > 0 ? `${listId}-${current}` : undefined}
        aria-invalid={invalid}
        aria-describedby={describedBy}
        autoComplete="off"
        placeholder={placeholder}
        maxLength={maxLength}
        value={value}
        onChange={(e) => {
          onType(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          setOpen(false);
          onBlurText?.(value);
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" && choices.length) {
            e.preventDefault();
            setOpen(true);
            setActive((current + 1) % choices.length);
          } else if (e.key === "ArrowUp" && choices.length) {
            e.preventDefault();
            setActive((current - 1 + choices.length) % choices.length);
          } else if (e.key === "Enter" && shown && choices[current]) {
            e.preventDefault(); // choose the highlighted one instead of submitting the form
            pick(choices[current]);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {shown && (
        <ul
          id={listId}
          role="listbox"
          className="absolute left-0 right-0 top-[calc(100%+0.3rem)] z-20 m-0 max-h-[15rem] list-none overflow-y-auto rounded-[0.9rem] bg-white p-1.5 shadow-[0_18px_40px_-14px_rgba(60,20,30,0.4),0_0_0_1px_rgba(60,20,30,0.08)]"
        >
          {choices.length === 0 && emptyNote && (
            <li className="px-3 py-2.5 text-[0.8rem] text-muted">{emptyNote}</li>
          )}
          {choices.map((choice, i) => (
            <li
              key={choice.key}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === current}
              // mouse down, not click: the box would lose focus (and close the list) before a click arrived
              onMouseDown={(e) => {
                e.preventDefault();
                pick(choice);
              }}
              onMouseEnter={() => setActive(i)}
              className={`flex cursor-pointer items-baseline justify-between gap-3 rounded-[0.65rem] px-3 py-2 text-[0.86rem] font-semibold ${
                i === current ? "bg-[#fbeff2] text-ink" : "text-slate-ink"
              }`}
            >
              <span className="min-w-0 truncate">
                <Highlight label={choice.label} typed={value.trim()} />
              </span>
              {choice.hint && <span className="flex-none text-[0.72rem] font-medium text-muted">{choice.hint}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
