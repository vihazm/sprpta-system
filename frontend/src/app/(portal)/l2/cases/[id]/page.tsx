import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Note } from "@/components/dashboard/Note";
import { loadCase } from "@/components/l2/api";
import { CaseReview } from "@/components/l2/case/CaseReview";
import { CaseReviewSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";

export const metadata: Metadata = { title: "Case | SPRPTA" };

async function Case({ params }: { params: PageProps<"/l2/cases/[id]">["params"] }) {
  const id = Number((await params).id);
  if (!Number.isSafeInteger(id) || id < 1) notFound();
  const result = await loadCase(id);
  if (!result.ok) {
    if (result.status === 404) notFound();
    return <Note tone="alert">{result.message}</Note>;
  }
  return <CaseReview initial={result.data} />;
}

export default function Page({ params }: PageProps<"/l2/cases/[id]">) {
  return (
    <Suspense fallback={<CaseReviewSkeleton />}>
      <Reveal>
        <Case params={params} />
      </Reveal>
    </Suspense>
  );
}
