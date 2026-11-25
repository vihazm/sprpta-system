"use client";

import { useRef } from "react";

const LENGTH = 6;

export const EMPTY_CODE: string[] = Array.from({ length: LENGTH }, () => "");

/**
 * Six boxes for the one-time code. Typing moves on, Backspace goes back, and a pasted code fills them all.
 * The code is a list of six single characters. Changes arrive as a function of the previous list, so fast typing
 * can never overwrite an earlier digit.
 */
export function OtpInput({
  value,
  onChange,
  invalid,
  disabled,
  describedBy,
}: {
  value: string[];
  onChange: (update: (previous: string[]) => string[]) => void;
  invalid: boolean;
  disabled: boolean;
  describedBy: string;
}) {
  const boxes = useRef<(HTMLInputElement | null)[]>([]);

  function set(index: number, digit: string) {
    onChange((previous) => previous.map((old, i) => (i === index ? digit : old)));
  }

  return (
    <div className="flex justify-between gap-[0.55rem]" role="group" aria-label="Verification code">
      {value.map((digit, i) => (
        <input
          key={i}
          ref={(el) => {
            boxes.current[i] = el;
          }}
          value={digit}
          disabled={disabled}
          inputMode="numeric"
          autoComplete={i === 0 ? "one-time-code" : "off"}
          maxLength={1}
          aria-label={`Digit ${i + 1}`}
          aria-invalid={invalid}
          aria-describedby={describedBy}
          onChange={(e) => {
            const typed = e.target.value.replace(/\D/g, "").slice(-1);
            set(i, typed);
            if (typed && i < LENGTH - 1) boxes.current[i + 1]?.focus();
          }}
          onFocus={(e) => e.target.select()}
          onKeyDown={(e) => {
            if (e.key === "Backspace" && !digit && i > 0) boxes.current[i - 1]?.focus();
          }}
          onPaste={(e) => {
            const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, LENGTH);
            if (!pasted) return;
            e.preventDefault();
            onChange(() => Array.from({ length: LENGTH }, (_, i) => pasted[i] ?? ""));
            boxes.current[Math.min(pasted.length, LENGTH - 1)]?.focus();
          }}
          className="focus-ring h-[3.9rem] w-full min-w-0 rounded-[1rem] border-[1.5px] border-transparent bg-field text-center font-display text-[1.6rem] text-ink outline-none transition focus:border-crimson focus:bg-white focus:shadow-[0_0_0_0.25rem_rgba(179,17,47,0.12)] aria-[invalid=true]:border-error aria-[invalid=true]:bg-[#FFF6F5] max-[599px]:h-[3.2rem] max-[599px]:text-[1.3rem]"
        />
      ))}
    </div>
  );
}
