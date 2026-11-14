import type { Metadata } from "next";
import { RecommendationForm } from "@/components/l1/dashboard/RecommendationForm";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "New recommendation | SPRPTA" };

export default function Page() {
  return (
    <WelcomePanel screen="New recommendation">
      <RecommendationForm className="max-w-[44rem]" />
    </WelcomePanel>
  );
}
