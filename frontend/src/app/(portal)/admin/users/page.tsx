import type { Metadata } from "next";
import { UsersPage } from "@/components/admin/users/UsersPage";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Users | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="Users">
      <UsersPage />
    </WelcomePanel>
  );
}
