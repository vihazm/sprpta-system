import type { ReactNode } from "react";
import { PortalShell } from "@/components/portal/PortalShell";

// Level 1 office staff area. Everything under /l1 requires the "l1" role.
export default function L1Layout({ children }: { children: ReactNode }) {
  return <PortalShell role="l1">{children}</PortalShell>;
}
