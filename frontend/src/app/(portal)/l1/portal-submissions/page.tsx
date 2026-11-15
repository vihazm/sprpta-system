import type { Metadata } from "next";
import { PortalSubmissionsPage } from "@/components/l1/complaints/PortalSubmissionsPage";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Portal submissions | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="Portal submissions">
      <PortalSubmissionsPage />
    </WelcomePanel>
  );
}