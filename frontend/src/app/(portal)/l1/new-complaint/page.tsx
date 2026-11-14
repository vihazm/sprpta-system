import type { Metadata } from "next";
import { Suspense } from "react";
import { NewComplaint } from "@/components/l1/entry/NewComplaint";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "New complaint | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="New complaint">
      <Suspense>
        <NewComplaint />
      </Suspense>
    </WelcomePanel>
  );
}
