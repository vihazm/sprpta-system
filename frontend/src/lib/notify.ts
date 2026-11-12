// Sitewide notifications ("island pill"). Client-side only.
//
//   import { notify } from "@/lib/notify";
//   notify.success("Saved", "The complaint was forwarded.");
//   notify.error("Could not save", "Please check the highlighted fields.");
//
// Green is for good news, red for bad news. One message shows at a time (a new
// one replaces the old). The <Toaster /> in the root layout draws it, so any
// client component or event handler can call this without extra setup.
// Use it instead of alert(), confirm() or the browser's own form bubbles.

type NotifyKind = "success" | "error";

export type Toast = {
  id: number;
  kind: NotifyKind;
  title: string;
  message?: string;
  /** How long it stays, in milliseconds. */
  duration: number;
};

type NotifyOptions = { duration?: number };

const DEFAULT_DURATION: Record<NotifyKind, number> = {
  success: 4000,
  error: 7000, // errors stay longer: people need time to read what went wrong
};

let current: Toast | null = null;
let nextId = 1;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((listener) => listener());
}

function show(kind: NotifyKind, title: string, message?: string, options?: NotifyOptions) {
  current = {
    id: nextId++,
    kind,
    title,
    message,
    duration: options?.duration ?? DEFAULT_DURATION[kind],
  };
  emit();
}

/** Used by the <Toaster />. */
export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSnapshot(): Toast | null {
  return current;
}

/** Removes the toast with this id (no-op if a newer one has replaced it). */
export function remove(id: number) {
  if (current?.id === id) {
    current = null;
    emit();
  }
}

export const notify = {
  success: (title: string, message?: string, options?: NotifyOptions) =>
    show("success", title, message, options),
  error: (title: string, message?: string, options?: NotifyOptions) =>
    show("error", title, message, options),
  /** Close whatever is showing. */
  dismiss: () => {
    if (current) remove(current.id);
  },
};
