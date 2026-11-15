import type { Metadata } from "next";
import { Suspense } from "react";
import { UsersPage } from "@/components/admin/users/UsersPage";
import { UsersSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Users | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="Users">
      <Suspense fallback={<UsersSkeleton />}>
        <Reveal>
          <UsersPage />
        </Reveal>
      </Suspense>
    </WelcomePanel>
  );
}
