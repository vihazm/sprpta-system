import type { ReactNode } from "react";
import { PortalFrame } from "@/components/portal/PortalFrame";

// Implementing staff area. Everything under /is requires the "implementing_staff" role.
export default function ImplementingStaffLayout({ children }: { children: ReactNode }) {
  return <PortalFrame role="implementing_staff">{children}</PortalFrame>;
}
