import type { Metadata } from "next";
import { Suspense } from "react";
import { ComplaintsPage } from "@/components/l1/complaints/ComplaintsPage";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "My Complaints | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="My Complaints">
      <Suspense>
        <ComplaintsPage />
      </Suspense>
    </WelcomePanel>
  );
}