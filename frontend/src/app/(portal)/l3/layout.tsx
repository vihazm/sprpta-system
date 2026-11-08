import type { ReactNode } from "react";
import { PortalFrame } from "@/components/portal/PortalFrame";

// Level 3 chairman area. Everything under /l3 requires the "l3" role.
export default function L3Layout({ children }: { children: ReactNode }) {
  return <PortalFrame role="l3">{children}</PortalFrame>;
}
