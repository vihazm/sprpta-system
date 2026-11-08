import type { ReactNode } from "react";
import { PortalFrame } from "@/components/portal/PortalFrame";

// Level 2 area officer area. Everything under /l2 requires the "l2" role.
export default function L2Layout({ children }: { children: ReactNode }) {
  return <PortalFrame role="l2">{children}</PortalFrame>;
}
