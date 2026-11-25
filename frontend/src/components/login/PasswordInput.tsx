"use client";

import { useState } from "react";

const inputClass =
  "h-[3.1rem] w-full rounded-[0.95rem] border-[1.5px] border-[#e4dde0] bg-field pl-[1.05rem] pr-[3.2rem] text-[0.96rem] font-medium text-ink outline-none transition placeholder:text-[#6F7682] focus:border-crimson focus:bg-white focus:shadow-[0_0_0_0.25rem_rgba(179,17,47,0.12)] aria-[invalid=true]:border-error aria-[invalid=true]:bg-[#FFF6F5]";

const ICON = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

/** A password box with an eye button that shows or hides what was typed. Used by sign-in and sign-up. */
export function PasswordInput({
  id,
  value,
  onChange,
  onBlur,
  autoComplete,
  placeholder,
  invalid = false,
  describedBy,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  autoComplete: "current-password" | "new-password";
  placeholder?: string;
  invalid?: boolean;
  describedBy?: string;
}) {
  const [visible, setVisible] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  return (
    <div className="relative">
      <input
        id={id}
        className={inputClass}
        type={visible ? "text" : "password"}
        autoComplete={autoComplete}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={() => {
          setCapsLock(false);
          onBlur?.();
        }}
        onKeyUp={(e) => setCapsLock(e.getModifierState("CapsLock"))}
        aria-invalid={invalid}
        aria-describedby={describedBy}
      />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? "Hide password" : "Show password"}
        aria-pressed={visible}
        className="focus-ring absolute right-[0.35rem] top-[0.35rem] grid size-[2.4rem] cursor-pointer place-items-center rounded-[0.65rem] border-0 bg-transparent text-muted transition-colors hover:bg-black/5 hover:text-crimson"
      >
        {visible ? (
          <svg {...ICON} aria-hidden="true">
            <path d="M3 3l18 18" />
            <path d="M10.6 6.2A9.9 9.9 0 0 1 12 6c5 0 8.5 4 9.5 6a12.6 12.6 0 0 1-2.6 3.3M6.6 7.6A12.4 12.4 0 0 0 2.5 12c1 2 4.5 6 9.5 6a9.7 9.7 0 0 0 4-.9" />
            <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
          </svg>
        ) : (
          <svg {...ICON} aria-hidden="true">
            <path d="M2.5 12S6 6 12 6s9.5 6 9.5 6-3.5 6-9.5 6S2.5 12 2.5 12z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )}
      </button>
      {capsLock && (
        <p role="status" className="m-0 mt-[0.4rem] text-[0.76rem] font-semibold text-[#92400e]">
          Caps Lock is on.
        </p>
      )}
    </div>
  );
}
