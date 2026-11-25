import type { Metadata } from "next";
import { Suspense } from "react";
import { loadComplaints } from "@/components/cp/api";
import { MyComplaints } from "@/components/cp/MyComplaints";
import { Card } from "@/components/dashboard/ui";
import { CpComplaintsSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";

export const metadata: Metadata = { title: "My complaints | SPRPTA" };

// The complaints are read here, while the page is built. ?id= opens one of them (a link from the dashboard).
async function Complaints({ searchParams }: { searchParams: Promise<{ id?: string }> }) {
  const [result, { id }] = await Promise.all([loadComplaints(), searchParams]);
  if (!result.ok) {
    return (
      <Card>
        <p className="text-[0.9rem] font-bold text-error">Your complaints could not be loaded.</p>
        <p className="text-[0.78rem] text-muted">{result.message}</p>
      </Card>
    );
  }
  const selected = Number(id);
  return <MyComplaints complaints={result.data} selectedId={Number.isInteger(selected) ? selected : null} />;
}

export default function Page({ searchParams }: { searchParams: Promise<{ id?: string }> }) {
  return (
    <Suspense fallback={<CpComplaintsSkeleton />}>
      <Reveal>
        <Complaints searchParams={searchParams} />
      </Reveal>
    </Suspense>
  );
}
