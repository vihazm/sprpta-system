import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { loadRecords } from "@/components/admin/master-data/api";
import { isEntityKey } from "@/components/admin/master-data/entities";
import { RecordDirectory } from "@/components/admin/master-data/RecordDirectory";
import { RecordsSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Master data | SPRPTA" };

async function Records({ params }: { params: PageProps<"/admin/master-data/[entity]">["params"] }) {
  const { entity } = await params;
  if (!isEntityKey(entity)) notFound();
  const firstPage = await loadRecords(entity);
  return <RecordDirectory key={entity} entityKey={entity} initial={firstPage.ok ? firstPage.data : undefined} />;
}

export default function Page({ params }: PageProps<"/admin/master-data/[entity]">) {
  return (
    <WelcomePanel screen="Master data">
      <Suspense fallback={<RecordsSkeleton />}>
        <Reveal>
          <Records params={params} />
        </Reveal>
      </Suspense>
    </WelcomePanel>
  );
}
