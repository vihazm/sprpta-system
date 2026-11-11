import type { Metadata } from "next";
import { L2Dashboard } from "@/components/l2/dashboard/L2Dashboard";

export const metadata: Metadata = { title: "Dashboard | SPRPTA" };

export default function Page() {
  return <L2Dashboard />;
}
