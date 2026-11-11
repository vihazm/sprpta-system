import type { Tone } from "@/components/dashboard/ui";
import type { RatingBand } from "./types";

// Colours for the four rating bands (90 to 100, 75 to 89, 60 to 74, below 60).
export const BAND_TONE: Record<RatingBand, Tone> = {
  Excellent: "ok",
  Good: "info",
  "Needs improvement": "warn",
  Poor: "crit",
};

export const BAND_TILE: Record<RatingBand, string> = {
  Excellent: "bg-emerald-50",
  Good: "bg-slate-100",
  "Needs improvement": "bg-amber-50",
  Poor: "bg-red-50",
};
