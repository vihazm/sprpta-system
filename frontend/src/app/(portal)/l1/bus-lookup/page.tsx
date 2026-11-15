import type { Metadata } from "next";
import { Suspense } from "react";
import { BusLookup } from "@/components/l1/lookup/BusLookup";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Bus & permit lookup | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="Bus & permit lookup">
      <Suspense>
        <BusLookup />
      </Suspense>
    </WelcomePanel>
  );
}
