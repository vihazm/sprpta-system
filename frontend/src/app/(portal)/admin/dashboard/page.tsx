import type { Metadata } from "next";
import { Suspense } from "react";
import { AdminDashboard } from "@/components/admin/dashboard/AdminDashboard";
import { AdminDashboardSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Dashboard | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="Dashboard">
      <Suspense fallback={<AdminDashboardSkeleton />}>
        <Reveal>
          <AdminDashboard />
        </Reveal>
      </Suspense>
    </WelcomePanel>
  );
}
