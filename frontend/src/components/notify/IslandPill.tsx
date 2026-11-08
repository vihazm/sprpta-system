"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Toast } from "@/lib/notify";
import { AlertIcon, CheckIcon, CloseIcon } from "./icons";

// Timing of the sequence: pop in, open to the message, (wait), fold, leave.
const OPEN_DELAY = 340;
const FOLD_TIME = 380;
const LEAVE_TIME = 300;
const MAX_WIDTH = 640; // px, the widest the pill may grow
const SIDE_GUTTER = 24; // px kept free at the screen edges

const EASE_OUT = "cubic-bezier(0.22, 1, 0.36, 1)";

/**
 * One notification, drawn as a dark pill at the top centre with a glowing green
 * (success) or red (error) dot. It pops in as icon + title, then opens
 * smoothly to its exact message width. If the message cannot fit on one line
 * (small phones), the message unfolds underneath instead, so the pill never
 * squashes the text. Pauses while hovered or focused; closes with the X
 * button, the Escape key, or on its own after toast.duration.
 */
export function IslandPill({
  toast,
  onRemove,
}: {
  toast: Toast;
  onRemove: (id: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [layout, setLayout] = useState<{
    mode: "inline" | "stacked";
    width: number; // inline: the message's own width
    closed: number; // stacked: the pill's width before opening
    limit: number; // stacked: the pill's width once open
  }>({ mode: "inline", width: 0, closed: 0, limit: 0 });
  const pillRef = useRef<HTMLDivElement>(null);
  const messageRef = useRef<HTMLSpanElement>(null);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const dismissTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const remaining = useRef(toast.duration + OPEN_DELAY);
  const startedAt = useRef(0);
  const closing = useRef(false);
  const isError = toast.kind === "error";

  const close = useCallback(() => {
    if (closing.current) return;
    closing.current = true;
    clearTimeout(dismissTimer.current);
    setOpen(false);
    timers.current.push(
      setTimeout(() => setLeaving(true), FOLD_TIME),
      setTimeout(() => onRemove(toast.id), FOLD_TIME + LEAVE_TIME),
    );
  }, [onRemove, toast.id]);

  const startDismissTimer = useCallback(() => {
    startedAt.current = Date.now();
    dismissTimer.current = setTimeout(close, remaining.current);
  }, [close]);

  const pause = useCallback(() => {
    if (closing.current) return;
    clearTimeout(dismissTimer.current);
    remaining.current -= Date.now() - startedAt.current;
  }, []);

  const resume = useCallback(() => {
    if (closing.current) return;
    clearTimeout(dismissTimer.current);
    startDismissTimer();
  }, [startDismissTimer]);

  // Measure the message once the pill is on screen, then open it.
  const openUp = useCallback(() => {
    const pill = pillRef.current;
    const message = messageRef.current;
    if (!pill || !message) {
      setOpen(true);
      return;
    }
    const natural = message.scrollWidth; // one-line width, including its divider
    const closedWidth = pill.offsetWidth;
    const limit = Math.min(MAX_WIDTH, window.innerWidth - SIDE_GUTTER);
    if (natural <= limit - closedWidth) {
      setLayout({ mode: "inline", width: natural, closed: closedWidth, limit });
      setOpen(true);
    } else {
      // Too long for one line: widen the pill and unfold the message beneath the title.
      setLayout({ mode: "stacked", width: 0, closed: closedWidth, limit });
      requestAnimationFrame(() => requestAnimationFrame(() => setOpen(true)));
    }
  }, []);

  useEffect(() => {
    const pending = timers.current;
    if (toast.message) pending.push(setTimeout(openUp, OPEN_DELAY));
    startDismissTimer();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      clearTimeout(dismissTimer.current);
      pending.forEach(clearTimeout);
    };
  }, [close, openUp, startDismissTimer, toast.message]);

  const stacked = layout.mode === "stacked";

  return (
    <div className="pointer-events-none fixed inset-x-0 top-[1rem] z-[100] flex justify-center px-[0.75rem]">
      <div
        ref={pillRef}
        role={isError ? "alert" : "status"}
        onPointerEnter={pause}
        onPointerLeave={resume}
        onFocus={pause}
        onBlur={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget)) resume();
        }}
        style={{
          transitionTimingFunction: EASE_OUT,
          // transform, opacity, width
          transitionDuration: `300ms, 300ms, ${open ? 560 : FOLD_TIME}ms`,
          ...(stacked ? { width: open ? layout.limit : layout.closed } : {}),
        }}
        // rounded-[1.5rem] is half the pill's height, so it is a perfect pill when
        // one line tall and keeps the same corners if the pill grows taller.
        className={`pointer-events-auto flex max-w-full bg-ink text-white shadow-[0_14px_30px_-10px_rgba(0,0,0,0.45)] transition-[transform,opacity,width] ${
          stacked ? "flex-col" : "items-center"
        } rounded-[1.5rem] ${leaving ? "-translate-y-2 scale-95 opacity-0" : "animate-island-in"}`}
      >
        <div className="flex w-full items-center py-[0.5rem] pl-[0.5rem] pr-[0.6rem]">
          <span
            className={`grid h-[2rem] w-[2rem] flex-none place-items-center rounded-full p-[0.45rem] text-ink ${
              isError
                ? "bg-bad-glow shadow-[0_0_0_0.25rem_rgba(248,113,113,0.2),0_0_1.1rem_rgba(248,113,113,0.55)]"
                : "bg-ok-glow shadow-[0_0_0_0.25rem_rgba(52,211,153,0.2),0_0_1.1rem_rgba(52,211,153,0.55)]"
            }`}
          >
            {isError ? <AlertIcon /> : <CheckIcon />}
          </span>
          <span className="ml-[0.65rem] whitespace-nowrap text-[0.9rem] font-extrabold">
            {toast.title}
          </span>

          {/* Message beside the title: the box grows to its exact measured width. */}
          {!stacked && toast.message && (
            <div
              style={{
                width: open ? layout.width : 0,
                transitionDuration: `${open ? 560 : FOLD_TIME}ms`,
                transitionTimingFunction: EASE_OUT,
              }}
              className="flex-none overflow-hidden transition-[width] will-change-[width]"
            >
              <span
                ref={messageRef}
                style={{
                  opacity: open ? 1 : 0,
                  transitionDelay: open ? "140ms" : "0ms",
                }}
                className="relative block whitespace-nowrap pl-[1.35rem] text-[0.85rem] font-medium leading-[1.35] text-[#d1d5db] transition-opacity duration-300 before:absolute before:left-[0.65rem] before:top-[12%] before:h-[76%] before:w-px before:bg-white/25"
              >
                {toast.message}
              </span>
            </div>
          )}

          {stacked && <span className="min-w-[0.65rem] flex-1" />}
          <button
            type="button"
            onClick={close}
            aria-label="Dismiss notification"
            className={`focus-ring ${stacked ? "" : "ml-[0.65rem]"} grid h-[1.7rem] w-[1.7rem] flex-none cursor-pointer place-items-center rounded-full p-[0.4rem] text-[#9aa0aa] transition-colors hover:bg-white/10 hover:text-white`}
          >
            <CloseIcon />
          </button>
        </div>

        {/* Narrow screens: the message unfolds beneath the title. */}
        {stacked && toast.message && (
          <div
            style={{
              transitionDuration: `${open ? 460 : FOLD_TIME}ms`,
              transitionTimingFunction: EASE_OUT,
            }}
            className={`grid transition-[grid-template-rows] ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}
          >
            <div className="overflow-hidden">
              <p
                style={{ opacity: open ? 1 : 0, transitionDelay: open ? "120ms" : "0ms" }}
                className="m-0 pb-[0.75rem] pl-[3.2rem] pr-[1.1rem] text-[0.85rem] font-medium leading-[1.4] text-[#d1d5db] transition-opacity duration-300"
              >
                {toast.message}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
