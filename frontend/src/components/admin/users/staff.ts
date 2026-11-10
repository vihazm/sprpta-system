import type { Tone } from "../dashboard/types";
import type { StaffRole, StaffStatus } from "./types";

export const ROLE_ORDER: StaffRole[] = ["l1", "l2", "l3", "admin", "implementing_staff"];

export const ROLE_SHORT: Record<StaffRole, string> = {
  l1: "Level 1",
  l2: "Level 2",
  l3: "Level 3",
  admin: "Admin",
  implementing_staff: "Implementing",
};

// Each role keeps one tint everywhere: avatars, and the share bar in the hero tile.
export const AVATAR_TINT: Record<StaffRole, string> = {
  l1: "bg-crimson/10 text-crimson-hover",
  l2: "bg-[#ffd9e0] text-[#7a0a22]",
  l3: "bg-[#f3eef0] text-crimson-deep",
  admin: "bg-slate-ink text-white",
  implementing_staff: "bg-slate-100 text-slate-700",
};

export const STATUS_LABEL: Record<StaffStatus, string> = {
  active: "Active",
  locked: "Locked",
  inactive: "Inactive",
};

export const STATUS_TONE: Record<StaffStatus, Tone> = {
  active: "ok",
  locked: "warn",
  inactive: "info",
};

// The chips in the hero box. "active" includes locked accounts; "locked" is only those.
export type StatusFilter = "active" | "inactive" | "locked" | null;

export function initials(name: string) {
  return name
    .split(" ")
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}
