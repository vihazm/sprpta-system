"use client";

import type { ComplaintPage } from "@/components/l1/dashboard/api";
import { ComplaintsList } from "./ComplaintsList";

// Complaints the public sent through the portal, waiting for Level 1's first check. Each opens in the complaint form,
// where Level 1 checks the bus, sets the severity and forwards, rejects or keeps it as incomplete.
// `initial` is the first view, loaded on the server together with the page.
export function PortalSubmissionsPage({ initial }: { initial?: ComplaintPage }) {
  return (
    <ComplaintsList
      title="Portal submissions"
      subtitle="Complaints the public sent through the portal, waiting for your check."
      filter="submitted"
      scope="all"
      fixed
      emptyText="No portal submissions are waiting. They appear here as complainants send them."
      initial={initial}
    />
  );
}
