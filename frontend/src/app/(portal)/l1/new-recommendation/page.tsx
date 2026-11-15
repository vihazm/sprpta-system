import type { Metadata } from "next";
import { Suspense } from "react";
import { RecommendationForm } from "@/components/l1/dashboard/RecommendationForm";
import { loadOptions } from "@/components/l1/entry/api";
import { RecommendationSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "New recommendation | SPRPTA" };

// The ways a recommendation can arrive are read here, while the page is built.
async function Form() {
  const options = await loadOptions();
  return <RecommendationForm className="max-w-[44rem]" initialMediums={options.ok ? options.data.mediums : undefined} />;
}

export default function Page() {
  return (
    <WelcomePanel screen="New recommendation">
      <Suspense fallback={<RecommendationSkeleton />}>
        <Reveal>
          <Form />
        </Reveal>
      </Suspense>
    </WelcomePanel>
  );
}
