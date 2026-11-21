"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { CharCount, textareaClass } from "./controls";
import { PillButton } from "./ui";

// Asks before an action that changes a case's status (UI Flow 1.2, rule 5). With `reasonLabel` the person must
// also give a reason, and Confirm stays disabled until there is one (shared component, UI Flow 7).
// Render it only while it should show: {asking && <ConfirmDialog ... />}. It opens as a modal when it mounts
// and, when it goes away, gives the focus back to the button that opened it.
export function ConfirmDialog({
  title,
  children,
  confirmLabel,
  reasonLabel,
  reasonMax,
  busy = false,
  onConfirm,
  onCancel,
}: {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  reasonLabel?: string;
  reasonMax?: number; // the longest reason the server accepts
  busy?: boolean;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<Element | null>(null); // the button that opened it, kept from the first time only
  const titleId = useId();
  const [reason, setReason] = useState("");

  useEffect(() => {
    opener.current ??= document.activeElement;
    dialog.current?.showModal();
    return () => {
      if (opener.current instanceof HTMLElement) opener.current.focus();
    };
  }, []);

  const missingReason = reasonLabel !== undefined && !reason.trim();

  return (
    <dialog
      ref={dialog}
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault(); // Escape goes through onCancel, so the parent decides when it closes
        if (!busy) onCancel();
      }}
      className="m-auto w-[min(32rem,calc(100vw-2rem))] rounded-[1.75rem] bg-white p-6 text-ink shadow-[0_30px_60px_-20px_rgba(60,20,30,0.45)] backdrop:bg-ink/40"
    >
      <div className="flex flex-col gap-4">
        <h2 id={titleId} className="text-[1.1rem] font-extrabold tracking-[-0.015em]">
          {title}
        </h2>
        <div className="text-[0.84rem] leading-[1.55] text-slate-ink">{children}</div>
        {reasonLabel !== undefined && (
          <label className="flex flex-col gap-[0.4rem]">
            <span className="text-[0.78rem] font-bold">{reasonLabel}</span>
            <textarea
              className={textareaClass}
              value={reason}
              maxLength={reasonMax}
              onChange={(e) => setReason(e.target.value)}
            />
            {reasonMax && <CharCount value={reason} max={reasonMax} />}
          </label>
        )}
        <div className="flex flex-wrap justify-end gap-2">
          <PillButton onClick={onCancel} disabled={busy}>
            Cancel
          </PillButton>
          <PillButton primary disabled={busy || missingReason} onClick={() => onConfirm(reason.trim())}>
            {busy ? "Working…" : confirmLabel}
          </PillButton>
        </div>
      </div>
    </dialog>
  );
}
