import { TIME_ZONE } from "@/components/dashboard/dates";
import type { Tone } from "@/components/dashboard/ui";
import type { PortalComplaint } from "./types";

// The four steps a complainant sees. The ten internal statuses never reach this screen.
export const STEPS = [
  { label: "Submitted", note: "Waiting for a Level 1 officer to check it." },
  { label: "Received", note: "Checked and registered by SPRPTA." },
  { label: "Action in progress", note: "A decision was made and is being carried out." },
  { label: "Closed", note: "The action is done and the case is closed." },
];

export function statusTone(c: PortalComplaint): "brand" | Tone {
  if (c.outcome === "not_accepted") return "info";
  return ({ 1: "brand", 2: "info", 3: "warn", 4: "ok" } as const)[c.step];
}

/** The sentence under a complaint's progress: what is happening now. */
export function whatNext(c: PortalComplaint): { title: string; detail: string } {
  if (c.outcome === "not_accepted") {
    return {
      title: "SPRPTA could not take this complaint further",
      detail: "It was checked and not accepted. If you think this is wrong, contact the SPRPTA office.",
    };
  }
  return {
    1: {
      title: "Waiting for SPRPTA to check it",
      detail: "A Level 1 officer checks every portal complaint first. You will get a message once it is registered.",
    },
    2: {
      title: "SPRPTA has registered your complaint",
      detail: "It was checked and passed to the officer for the area.",
    },
    3: {
      title: "Action is being carried out",
      detail: "A decision was made and the action is under way. You will be told when the case is closed.",
    },
    4: { title: "This complaint is closed", detail: "The decided action was completed and the case is closed." },
  }[c.step];
}

const dateFormat = new Intl.DateTimeFormat("en-GB", { timeZone: TIME_ZONE, day: "numeric", month: "short", year: "numeric" });

/** "24 Nov 2026" in Sri Lankan time, or an empty string when there is no date. */
export function formatDate(iso: string | null): string {
  return iso ? dateFormat.format(new Date(iso)) : "";
}

/** The reference number, or a plain note while Level 1 has not issued one. */
export function referenceText(c: PortalComplaint): string {
  return c.referenceNumber ?? "Reference not yet assigned";
}
