import type { Metadata } from "next";
import { Suspense } from "react";
import { BusLookup } from "@/components/l1/lookup/BusLookup";
import { listDailyRecords } from "@/components/l1/lookup/records-api";
import { BusLookupSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Bus & permit lookup | SPRPTA" };

// The officer's own daily records (the first page) are read here, while the page is built.
async function Lookup() {
  const records = await listDailyRecords({ date: "", search: "", page: 1 });
  return <BusLookup initialRecords={records.ok ? records.data : undefined} />;
}

export default function Page() {
  return (
    <WelcomePanel screen="Bus & permit lookup">
      <Suspense fallback={<BusLookupSkeleton />}>
        <Reveal>
          <Lookup />
        </Reveal>
      </Suspense>
    </WelcomePanel>
  );
}
