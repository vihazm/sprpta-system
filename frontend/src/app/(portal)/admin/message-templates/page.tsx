import type { Metadata } from "next";
import { Suspense } from "react";
import { MessageTemplates } from "@/components/admin/message-templates/MessageTemplates";
import { MessageTemplatesSkeleton } from "@/components/portal/PageSkeletons";
import { Reveal } from "@/components/portal/Reveal";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Message templates | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="Message templates">
      <Suspense fallback={<MessageTemplatesSkeleton />}>
        <Reveal>
          <MessageTemplates />
        </Reveal>
      </Suspense>
    </WelcomePanel>
  );
}
