"use client";

import type { ComplaintPage } from "@/components/l1/dashboard/api";
import { ComplaintsList } from "./ComplaintsList";

// Complaints the public sent through the portal, waiting for Level 1's first check. Reviewing one (checking the
// vehicle, setting the severity, forwarding) comes with the complainant portal, so for now they are listed only.
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
      notice="Reviewing a portal submission is not available yet: the complainant portal is still being built."
      initial={initial}
    />
  );
}
