import type { ReactNode } from "react";
import { PortalShell } from "@/components/portal/PortalShell";

// System administrator area. Everything under /admin requires the "admin" role.
export default function AdminLayout({ children }: { children: ReactNode }) {
  return <PortalShell role="admin">{children}</PortalShell>;
}
