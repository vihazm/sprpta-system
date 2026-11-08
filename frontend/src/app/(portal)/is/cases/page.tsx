import type { Metadata } from "next";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "Case search | SPRPTA" };

export default function Page() {
  return <WelcomePanel screen="Case search" />;
}
