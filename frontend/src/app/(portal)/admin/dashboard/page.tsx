import type { Metadata } from "next";
import { AdminDashboard } from "@/components/admin/dashboard/AdminDashboard";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Dashboard | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="Dashboard">
      <AdminDashboard />
    </WelcomePanel>
  );
}
