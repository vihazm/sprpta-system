import type { Metadata } from "next";
import { Suspense } from "react";
import { SystemHealth } from "@/components/admin/system-health/SystemHealth";
import { SystemHealthSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "System health | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="System health">
      <Suspense fallback={<SystemHealthSkeleton />}>
        <Reveal>
          <SystemHealth />
        </Reveal>
      </Suspense>
    </WelcomePanel>
  );
}
