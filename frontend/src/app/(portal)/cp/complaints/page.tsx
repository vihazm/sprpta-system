import type { Metadata } from "next";
import { WelcomePanel } from "@/components/portal/WelcomePanel";

export const metadata: Metadata = { title: "My complaints | SPRPTA" };

export default function Page() {
  return <WelcomePanel screen="My complaints" />;
}
