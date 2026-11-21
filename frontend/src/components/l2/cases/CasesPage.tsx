"use client";

import { useRouter } from "next/navigation";
import { CaseList } from "../CaseList";
import { STATUS_LABEL } from "../status";
import type { CaseFilter, CasePage } from "../types";

// The Cases page (UI-L2-02): every case of the officer's area, including escalated and closed ones, which open
// read-only. The status filter lives in the address (/l2/cases?status=overdue), so a view can be reloaded or shared.
export function CasesPage({ status, initial }: { status: CaseFilter | null; initial?: CasePage }) {
  const router = useRouter();

  return (
    <CaseList
      key={status ?? "all"} // a new filter in the address starts the list again, on its first page
      title="Cases in your area"
      subtitle={
        status
          ? `Filtered by ${status === "overdue" ? "Overdue" : STATUS_LABEL[status]}. Open a case to review it.`
          : "Every case forwarded to your area. Open a case to review it."
      }
      status={status}
      onStatus={(next) => router.replace(next ? `/l2/cases?status=${next}` : "/l2/cases")}
      sort="newest"
      initial={initial}
    />
  );
}
