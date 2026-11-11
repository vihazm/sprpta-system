import type { Metadata } from "next";
import { L1Dashboard } from "@/components/l1/dashboard/L1Dashboard";

export const metadata: Metadata = { title: "Dashboard | SPRPTA" };

export default function Page() {
  return <L1Dashboard />;
}
