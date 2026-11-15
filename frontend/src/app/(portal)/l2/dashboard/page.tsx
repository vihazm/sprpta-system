import type { Metadata } from "next";
import { Suspense } from "react";
import { L2Dashboard } from "@/components/l2/dashboard/L2Dashboard";
import { L2DashboardSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";

export const metadata: Metadata = { title: "Dashboard | SPRPTA" };

export default function Page() {
  return (
    <Suspense fallback={<L2DashboardSkeleton />}>
      <Reveal>
        <L2Dashboard />
      </Reveal>
    </Suspense>
  );
}
