import type { Metadata } from "next";
import { Suspense } from "react";
import { loadOptions } from "@/components/cp/api";
import { NewComplaintForm } from "@/components/cp/NewComplaintForm";
import { Card } from "@/components/dashboard/ui";
import { CpFormSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";

export const metadata: Metadata = { title: "New complaint | SPRPTA" };

// The lists the form offers are read here, while the page is built, so the form is there when the page is.
async function Form() {
  const options = await loadOptions();
  if (!options.ok) {
    return (
      <Card>
        <p className="text-[0.9rem] font-bold text-error">The form could not be loaded.</p>
        <p className="text-[0.78rem] text-muted">{options.message}</p>
      </Card>
    );
  }
  return <NewComplaintForm options={options.data} />;
}

export default function Page() {
  return (
    <Suspense fallback={<CpFormSkeleton />}>
      <Reveal>
        <Form />
      </Reveal>
    </Suspense>
  );
}
