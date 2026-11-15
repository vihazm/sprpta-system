"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardHeading } from "@/components/dashboard/ui";
import { BusLookupPanel } from "./BusLookupPanel";

// The Bus & permit lookup screen. "Use Details in Complaint" opens the New complaint form with the chosen record;
// when the officer came from a saved draft ("Reopen bus lookup"), it replaces that draft's bus instead.
export function BusLookup() {
  const router = useRouter();
  const draft = useSearchParams().get("complaint") ?? "";
  const complaintId = /^[1-9]\d{0,15}$/.test(draft) ? Number(draft) : undefined;

  return (
    <Card>
      <CardHeading
        title="Bus & permit lookup"
        subtitle="Find which trip a bus ran on the incident date, and who was on duty, from the published daily records."
      />
      <BusLookupPanel
        hint={complaintId ? "You are changing the bus of a saved complaint. Choose a record and use it to replace the bus." : undefined}
        onUse={(trip) => {
          const params = new URLSearchParams({ trip: String(trip.id) });
          if (complaintId) params.set("id", String(complaintId));
          router.push(`/l1/new-complaint?${params}`);
        }}
      />
    </Card>
  );
}
