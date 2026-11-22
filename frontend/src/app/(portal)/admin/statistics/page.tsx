import type { Metadata } from "next";
import { Suspense } from "react";
import { StatisticsPage } from "@/components/admin/statistics/StatisticsPage";
import { StatisticsSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Statistics and reports | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="Statistics and reports">
      <Suspense fallback={<StatisticsSkeleton />}>
        <Reveal>
          <StatisticsPage />
        </Reveal>
      </Suspense>
    </WelcomePanel>
  );
}
