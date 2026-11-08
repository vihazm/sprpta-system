import type { ReactNode } from "react";
import { PortalFrame } from "@/components/portal/PortalFrame";

// Level 1 office staff area. Everything under /l1 requires the "l1" role.
export default function L1Layout({ children }: { children: ReactNode }) {
  return <PortalFrame role="l1">{children}</PortalFrame>;
}
