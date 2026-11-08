import { Suspense, type ReactNode } from "react";
import type { Role } from "@/lib/roles";
import { PortalShell } from "./PortalShell";

/**
 * Use in a role's layout.tsx. The session check reads cookies, so it must sit
 * behind a Suspense boundary (Next.js Cache Components); the fallback below is
 * what shows for the instant before the check finishes.
 */
export function PortalFrame({ role, children }: { role: Role; children: ReactNode }) {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-page" aria-busy="true" />}>
      <PortalShell role={role}>{children}</PortalShell>
    </Suspense>
  );
}
