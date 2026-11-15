import type { ComplaintFilter, TargetFilter } from "@/components/l1/dashboard/api";

// The filters of the My Complaints page live in the address (/l1/complaints?target=driver&status=draft), so the
// dashboard cards can open a filtered view and the view can be shared or reloaded. The browser and the server
// both read them here, so the first view the server loads is the one the page then shows.

const FILTERS: ComplaintFilter[] = ["draft", "incomplete", "submitted", "forwarded", "rejected", "duplicates"];
const TARGETS: TargetFilter[] = ["driver", "conductor", "owner", "bus_service", "other", "unclassified"];

export type ComplaintsQuery = {
  filter: ComplaintFilter | null;
  target: TargetFilter | null;
  scope: "mine" | "all"; // the officer's own complaints, or the whole Level 1 queue
  verification: "failed" | "non_operating" | null;
  categoryId: number | null;
};

export function readComplaintsQuery(get: (name: string) => string | null | undefined): ComplaintsQuery {
  const verification = get("verification");
  return {
    filter: FILTERS.find((f) => f === get("status")) ?? null,
    target: TARGETS.find((t) => t === get("target")) ?? null,
    scope: get("scope") === "all" ? "all" : "mine",
    verification: verification === "failed" || verification === "non_operating" ? verification : null,
    categoryId: /^[1-9]\d{0,9}$/.test(get("category_id") ?? "") ? Number(get("category_id")) : null,
  };
}
