"use client";

import { useRouter, useSearchParams } from "next/navigation";
import type { ComplaintFilter, ComplaintPage, TargetFilter } from "@/components/l1/dashboard/api";
import { ComplaintsList } from "./ComplaintsList";
import { readComplaintsQuery } from "./query";

// My Complaints: the complaints this officer registered. The filters live in the address
// (/l1/complaints?target=driver&status=draft), so the dashboard cards can open a filtered view and the view can be
// shared or reloaded. scope=all shows the whole Level 1 queue, which the dashboard's queue cards open.
// `initial` is the first view, loaded on the server together with the page.
export function ComplaintsPage({ initial }: { initial?: ComplaintPage }) {
  const router = useRouter();
  const params = useSearchParams();
  const { filter, target, scope, verification, categoryId } = readComplaintsQuery((name) => params.get(name));

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
      initial={initial}
    />
  );
}
