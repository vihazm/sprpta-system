import type { ReactNode } from "react";
import { ComplainantShell } from "@/components/cp/ComplainantShell";

// Complainant portal area. Everything under /cp requires the "cp" role.
export default function ComplainantLayout({ children }: { children: ReactNode }) {
  return <ComplainantShell>{children}</ComplainantShell>;
}
