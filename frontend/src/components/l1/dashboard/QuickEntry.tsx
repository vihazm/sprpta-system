"use client";

import { Card, muted } from "@/components/dashboard/ui";
import { ComplaintForm } from "@/components/l1/entry/ComplaintForm";
import { useDashboard } from "./DashboardData";

// Entering a complaint that arrived by any medium (UC-L1-01 to UC-L1-10), all in one place. The dashboard's numbers
// are read again after each save, so the queues and Your day so far stay true.
export function QuickEntry({ className = "" }: { className?: string }) {
  const { refresh } = useDashboard();
  return (
    <Card className={`gap-4 ${className}`}>
      <div>
        <h3 className="text-[1.25rem] font-extrabold tracking-[-0.015em]">Quick entry</h3>
        <p className={`mt-0.5 ${muted}`}>
          Every detail of a complaint in one place. Details filled in from the records are shown in green.
        </p>
      </div>
      <ComplaintForm layout="quick" onChanged={refresh} />
    </Card>
  );
}