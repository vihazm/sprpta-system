import type { Metadata } from "next";
import { Suspense } from "react";
import { MasterDataHub } from "@/components/admin/master-data/MasterDataHub";
import { MasterDataSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Master data | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="Master data">
      <Suspense fallback={<MasterDataSkeleton />}>
        <Reveal>
          <MasterDataHub />
        </Reveal>
      </Suspense>
    </WelcomePanel>
  );
}
