import type { ReactNode } from "react";
import { PortalFrame } from "@/components/portal/PortalFrame";

// System administrator area. Everything under /admin requires the "admin" role.
export default function AdminLayout({ children }: { children: ReactNode }) {
  return <PortalFrame role="admin">{children}</PortalFrame>;
}
