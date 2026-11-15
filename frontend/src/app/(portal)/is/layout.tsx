import type { ReactNode } from "react";
import { PortalShell } from "@/components/portal/PortalShell";

// Implementing staff area. Everything under /is requires the "implementing_staff" role.
export default function ImplementingStaffLayout({ children }: { children: ReactNode }) {
  return <PortalShell role="implementing_staff">{children}</PortalShell>;
}
