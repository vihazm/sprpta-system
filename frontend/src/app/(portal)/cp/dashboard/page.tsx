import type { Metadata } from "next";
import { Suspense } from "react";
import { CpDashboard } from "@/components/cp/CpDashboard";
import { CpDashboardSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";

export const metadata: Metadata = { title: "Dashboard | SPRPTA" };

export default function Page() {
  return (
    <Suspense fallback={<CpDashboardSkeleton />}>
      <Reveal>
        <CpDashboard />
      </Reveal>
    </Suspense>
  );
}
