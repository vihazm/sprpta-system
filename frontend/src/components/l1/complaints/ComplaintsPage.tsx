"use client";

import { useRouter, useSearchParams } from "next/navigation";
import type { ComplaintFilter, TargetFilter } from "@/components/l1/dashboard/api";
import { ComplaintsList } from "./ComplaintsList";

const FILTERS: ComplaintFilter[] = ["draft", "incomplete", "submitted", "forwarded", "rejected", "duplicates"];
const TARGETS: TargetFilter[] = ["driver", "conductor", "owner", "bus_service", "other", "unclassified"];

// My Complaints: the complaints this officer registered. The filters live in the address
// (/l1/complaints?target=driver&status=draft), so the dashboard cards can open a filtered view and the view can be
// shared or reloaded. scope=all shows the whole Level 1 queue, which the dashboard's queue cards open.
export function ComplaintsPage() {
  const router = useRouter();
  const params = useSearchParams();
  const filter = FILTERS.find((f) => f === params.get("status")) ?? null;
  const target = TARGETS.find((t) => t === params.get("target")) ?? null;
  const scope = params.get("scope") === "all" ? "all" : "mine";
  const verification = params.get("verification") === "failed" || params.get("verification") === "non_operating"
    ? (params.get("verification") as "failed" | "non_operating")
    : null;
  const categoryId = /^[1-9]\d{0,9}$/.test(params.get("category_id") ?? "") ? Number(params.get("category_id")) : null;

  function open(next: { status?: ComplaintFilter | null; target?: TargetFilter | null }) {
    const query = new URLSearchParams();
    const status = next.status === undefined ? filter : next.status;
    const kind = next.target === undefined ? target : next.target;
    if (status) query.set("status", status);
    if (kind) query.set("target", kind);
    if (scope === "all") query.set("scope", "all");
    if (verification) query.set("verification", verification);
    if (categoryId) query.set("category_id", String(categoryId));
    router.replace(query.size ? `/l1/complaints?${query}` : "/l1/complaints");
  }

  return (
    <ComplaintsList
      title={scope === "all" ? "All Level 1 complaints" : "My Complaints"}
      subtitle={
        scope === "all"
          ? "Every complaint in the Level 1 queue, whoever entered it. Open a draft or an incomplete case to finish it."
          : "The complaints you registered, by who they are against. Open a draft or an incomplete case to finish it."
      }
      filter={filter}
      onFilter={(next) => open({ status: next })}
      target={target}
      onTarget={(next) => open({ target: next })}
      scope={scope}
      categoryId={categoryId}
      verification={verification}
      onClearFilter={() => router.replace("/l1/complaints")}
      emptyText="No complaints here yet."
    />
  );
}