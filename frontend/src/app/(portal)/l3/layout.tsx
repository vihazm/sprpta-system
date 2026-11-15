import type { ReactNode } from "react";
import { PortalShell } from "@/components/portal/PortalShell";

// Level 3 chairman area. Everything under /l3 requires the "l3" role.
export default function L3Layout({ children }: { children: ReactNode }) {
  return <PortalShell role="l3">{children}</PortalShell>;
}
