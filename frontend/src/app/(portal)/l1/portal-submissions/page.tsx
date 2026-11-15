import type { Metadata } from "next";
import { Suspense } from "react";
import { listComplaints } from "@/components/l1/dashboard/api";
import { PortalSubmissionsPage } from "@/components/l1/complaints/PortalSubmissionsPage";
import { ComplaintsSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Portal submissions | SPRPTA" };

// The first view of the list is read here, while the page is built.
async function Submissions() {
  const first = await listComplaints({ status: "submitted", target: null, scope: "all", search: "", page: 1 });
  return <PortalSubmissionsPage initial={first.ok ? first.data : undefined} />;
}

export default function Page() {
  return (
    <WelcomePanel screen="Portal submissions">
      <Suspense fallback={<ComplaintsSkeleton />}>
        <Reveal>
          <Submissions />
        </Reveal>
      </Suspense>
    </WelcomePanel>
  );
}
