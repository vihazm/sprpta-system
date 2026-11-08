import type { ReactNode } from "react";
import { PortalFrame } from "@/components/portal/PortalFrame";

// Complainant portal area. Everything under /cp requires the "cp" role.
export default function ComplainantLayout({ children }: { children: ReactNode }) {
  return <PortalFrame role="cp">{children}</PortalFrame>;
}
