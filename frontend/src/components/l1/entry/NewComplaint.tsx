"use client";

import { useSearchParams } from "next/navigation";
import { Card, muted } from "@/components/dashboard/ui";
import { ComplaintForm } from "./ComplaintForm";

// The full New complaint screen (UI-L1-03): the same form as the dashboard's Quick entry.
// With ?id=12 in the address it continues that saved draft or incomplete complaint; with ?trip=5 it starts
// a new one filled in from that daily record (Use Details in Complaint, in the Bus & Permit Lookup). With both,
// the saved complaint's bus is replaced by that record.
export function NewComplaint() {
  const params = useSearchParams();
  const positive = (text: string | null) => (/^[1-9]\d{0,15}$/.test(text ?? "") ? Number(text) : undefined);
  const complaintId = positive(params.get("id"));
  const tripId = positive(params.get("trip")); // a daily record chosen in the Bus & Permit Lookup

  return (
    <Card>
      <div>
        <h2 className="text-[1.25rem] font-extrabold tracking-[-0.015em]">
          {complaintId ? "Continue a complaint" : "New complaint"}
        </h2>
        <p className={`mt-0.5 ${muted}`}>
          Enter a complaint that reached SPRPTA by email, letter, WhatsApp, SMS or any other way. Details filled in from
          the records are shown in green.
        </p>
      </div>
      <ComplaintForm complaintId={complaintId} tripId={tripId} />
    </Card>
  );
}
