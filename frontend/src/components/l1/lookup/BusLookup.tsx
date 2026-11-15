"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Icon } from "@/components/dashboard/icons";
import { Card, CardHeading, PillButton } from "@/components/dashboard/ui";
import { BusLookupPanel } from "./BusLookupPanel";
import { DailyRecordForm } from "./DailyRecordForm";
import { MyDailyRecords } from "./MyDailyRecords";

// The Bus & permit lookup screen. "Use Details in Complaint" opens the New complaint form with the chosen record;
// when the officer came from a saved draft ("Reopen bus lookup"), it replaces that draft's bus instead.
// "Add Daily Bus Record" opens the entry form; what is saved there waits as Pending Verification for Admin.
export function BusLookup() {
  const router = useRouter();
  const draft = useSearchParams().get("complaint") ?? "";
  const complaintId = /^[1-9]\d{0,15}$/.test(draft) ? Number(draft) : undefined;
  // null: closed; 0: a new record; any other number: that saved record
  const [editing, setEditing] = useState<number | null>(null);
  const [refresh, setRefresh] = useState(0);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeading
          title="Bus & permit lookup"
          subtitle="Find which trip a bus ran on the incident date, and who was on duty, from the published daily records."
          action={
            editing === null ? (
              <PillButton primary onClick={() => setEditing(0)}>
                <Icon name="plus" size={13} />
                Add Daily Bus Record
              </PillButton>
            ) : undefined
          }
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

      {editing !== null && (
        <Card>
          <CardHeading
            title={editing === 0 ? "Add Daily Bus Record" : "Daily Bus Record"}
            subtitle="Saved as Pending Verification. System Admin verifies and publishes it before it appears in the lookup."
          />
          <DailyRecordForm
            key={editing}
            recordId={editing === 0 ? undefined : editing}
            onSaved={() => {
              setRefresh((n) => n + 1);
              setEditing(null);
            }}
            onClose={() => setEditing(null)}
          />
        </Card>
      )}

      <MyDailyRecords refresh={refresh} onOpen={(id) => setEditing(id)} />
    </div>
  );
}
