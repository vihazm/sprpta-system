import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Note } from "@/components/dashboard/Note";
import { loadRecommendation } from "@/components/l2/api";
import { RecommendationView } from "@/components/l2/recommendations/RecommendationView";
import { RecommendationSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";

export const metadata: Metadata = { title: "Recommendation | SPRPTA" };

async function Recommendation({ params }: { params: PageProps<"/l2/recommendations/[id]">["params"] }) {
  const id = Number((await params).id);
  if (!Number.isSafeInteger(id) || id < 1) notFound();
  const result = await loadRecommendation(id);
  if (!result.ok) {
    if (result.status === 404) notFound();
    return <Note tone="alert">{result.message}</Note>;
  }
  return <RecommendationView r={result.data} />;
}

export default function Page({ params }: PageProps<"/l2/recommendations/[id]">) {
  return (
    <Suspense fallback={<RecommendationSkeleton />}>
      <Reveal>
        <Recommendation params={params} />
      </Reveal>
    </Suspense>
  );
}
