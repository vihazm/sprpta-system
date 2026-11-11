import type { Metadata } from "next";
import { L3Dashboard } from "@/components/l3/dashboard/L3Dashboard";

export const metadata: Metadata = { title: "Dashboard | SPRPTA" };

export default function Page() {
  return <L3Dashboard />;
}
