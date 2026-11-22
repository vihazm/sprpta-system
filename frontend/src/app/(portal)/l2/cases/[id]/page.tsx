import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Note } from "@/components/dashboard/Note";
import { loadCase } from "@/components/l2/api";
import { CaseReview } from "@/components/l2/case/CaseReview";
import { CaseReviewSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";

export const metadata: Metadata = { title: "Case | SPRPTA" };

type Props = PageProps<"/l2/cases/[id]">;

async function Case({ params, searchParams }: Pick<Props, "params" | "searchParams">) {
  const id = Number((await params).id);
  if (!Number.isSafeInteger(id) || id < 1) notFound();
  const { from } = await searchParams; // set when opened from another case's earlier complaints
  const result = await loadCase(id);
  if (!result.ok) {
    if (result.status === 404) notFound();
    return <Note tone="alert">{result.message}</Note>;
  }
  return (
    <CaseReview
      key={id} // moving from one case to another starts the screen afresh
      initial={result.data}
      openedFrom={typeof from === "string" ? from.slice(0, 40) : null}
    />
  );
}

export default function Page({ params, searchParams }: Props) {
  return (
    <Suspense fallback={<CaseReviewSkeleton />}>
      <Reveal>
        <Case params={params} searchParams={searchParams} />
      </Reveal>
    </Suspense>
  );
}
