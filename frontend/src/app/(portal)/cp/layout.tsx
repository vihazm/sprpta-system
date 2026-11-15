import type { ReactNode } from "react";
import { PortalShell } from "@/components/portal/PortalShell";

// Complainant portal area. Everything under /cp requires the "cp" role.
export default function ComplainantLayout({ children }: { children: ReactNode }) {
  return <PortalShell role="cp">{children}</PortalShell>;
}
