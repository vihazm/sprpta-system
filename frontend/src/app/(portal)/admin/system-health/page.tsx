import type { Metadata } from "next";
import { SystemHealth } from "@/components/admin/system-health/SystemHealth";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "System health | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="System health">
      <SystemHealth />
    </WelcomePanel>
  );
}
