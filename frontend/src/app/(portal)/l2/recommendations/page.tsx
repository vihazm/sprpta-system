import type { Metadata } from "next";
import { Suspense } from "react";
import { listRecommendations } from "@/components/l2/api";
import { RecommendationsList } from "@/components/l2/recommendations/RecommendationsList";
import { RecommendationsSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";

export const metadata: Metadata = { title: "Recommendations | SPRPTA" };

async function Recommendations() {
  const first = await listRecommendations({ type: null, status: null, search: "", page: 1 });
  return <RecommendationsList initial={first.ok ? first.data : undefined} />;
}

export default function Page() {
  return (
    <Suspense fallback={<RecommendationsSkeleton />}>
      <Reveal>
        <Recommendations />
      </Reveal>
    </Suspense>
  );
}
