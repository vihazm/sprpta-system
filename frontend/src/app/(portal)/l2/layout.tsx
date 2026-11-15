import type { ReactNode } from "react";
import { PortalShell } from "@/components/portal/PortalShell";

// Level 2 area officer area. Everything under /l2 requires the "l2" role.
export default function L2Layout({ children }: { children: ReactNode }) {
  return <PortalShell role="l2">{children}</PortalShell>;
}
