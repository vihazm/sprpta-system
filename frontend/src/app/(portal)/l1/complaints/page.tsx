import type { Metadata } from "next";
import { Suspense } from "react";
import { listComplaints } from "@/components/l1/dashboard/api";
import { ComplaintsPage } from "@/components/l1/complaints/ComplaintsPage";
import { readComplaintsQuery } from "@/components/l1/complaints/query";
import { ComplaintsSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "My Complaints | SPRPTA" };

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

// The first view of the list is read here, while the page is built, using the filters in the address.
async function Complaints({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const query = readComplaintsQuery((name) => {
    const value = params[name];
    return Array.isArray(value) ? value[0] : value;
  });
  const first = await listComplaints({
    status: query.filter,
    target: query.target,
    scope: query.scope,
    categoryId: query.categoryId,
    verification: query.verification,
    search: "",
    page: 1,
  });
  return <ComplaintsPage initial={first.ok ? first.data : undefined} />;
}

export default function Page({ searchParams }: { searchParams: SearchParams }) {
  return (
    <WelcomePanel screen="My Complaints">
      <Suspense fallback={<ComplaintsSkeleton />}>
        <Reveal>
          <Complaints searchParams={searchParams} />
        </Reveal>
      </Suspense>
    </WelcomePanel>
  );
}
