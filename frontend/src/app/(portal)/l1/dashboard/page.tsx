import type { Metadata } from "next";
import { Suspense } from "react";
import { L1Dashboard } from "@/components/l1/dashboard/L1Dashboard";
import { L1DashboardSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";

export const metadata: Metadata = { title: "Dashboard | SPRPTA" };

export default function Page() {
  return (
    <Suspense fallback={<L1DashboardSkeleton />}>
      <Reveal>
        <L1Dashboard />
      </Reveal>
    </Suspense>
  );
}
