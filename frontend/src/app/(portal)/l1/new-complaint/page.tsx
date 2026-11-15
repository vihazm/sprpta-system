import type { Metadata } from "next";
import { Suspense } from "react";
import { loadOptions } from "@/components/l1/entry/api";
import { NewComplaint } from "@/components/l1/entry/NewComplaint";
import { NewComplaintSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "New complaint | SPRPTA" };

// The lists the form offers are read here, while the page is built, so the form is there when the page is.
async function Form() {
  const options = await loadOptions();
  return <NewComplaint options={options.ok ? options.data : undefined} />;
}

export default function Page() {
  return (
    <WelcomePanel screen="New complaint">
      <Suspense fallback={<NewComplaintSkeleton />}>
        <Reveal>
          <Form />
        </Reveal>
      </Suspense>
    </WelcomePanel>
  );
}
