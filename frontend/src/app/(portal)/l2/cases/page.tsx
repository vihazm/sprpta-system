import type { Metadata } from "next";
import { Suspense } from "react";
import { listCases } from "@/components/l2/api";
import { CasesPage } from "@/components/l2/cases/CasesPage";
import { STATUS_ORDER } from "@/components/l2/status";
import type { CaseFilter } from "@/components/l2/types";
import { CasesSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";

export const metadata: Metadata = { title: "Cases | SPRPTA" };

const FILTERS: string[] = [...STATUS_ORDER, "overdue"];

// The first view of the list is read here, while the page is built, using the filter in the address.
async function Cases({ searchParams }: { searchParams: PageProps<"/l2/cases">["searchParams"] }) {
  const { status: raw } = await searchParams;
  const status = typeof raw === "string" && FILTERS.includes(raw) ? (raw as CaseFilter) : null;
  const first = await listCases({ status, severity: null, search: "", sort: "newest", page: 1 });
  return <CasesPage status={status} initial={first.ok ? first.data : undefined} />;
}

export default function Page({ searchParams }: PageProps<"/l2/cases">) {
  return (
    <Suspense fallback={<CasesSkeleton />}>
      <Reveal>
        <Cases searchParams={searchParams} />
      </Reveal>
    </Suspense>
  );
}
