import type { Metadata } from "next";
import { Suspense } from "react";
import { L3Dashboard } from "@/components/l3/dashboard/L3Dashboard";
import { L3DashboardSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";

export const metadata: Metadata = { title: "Dashboard | SPRPTA" };

export default function Page() {
  return (
    <Suspense fallback={<L3DashboardSkeleton />}>
      <Reveal>
        <L3Dashboard />
      </Reveal>
    </Suspense>
  );
}
