"use client";

import { Icon } from "@/components/dashboard/icons";
import { Chip, PillButton } from "@/components/dashboard/ui";
import { toBusRecord } from "./api";
import { formatDay } from "./format";
import { copyRecord } from "./copy";
import { RecordFields, STATUS_TONE, VerificationNote } from "./RecordFields";
import type { TripDetails } from "./types";

// The record the officer chose (steps 5 and 6). "Use Details in Complaint" hands the record's id to the complaint
// form, which fills itself in from the verified record in the database, not from copied text.
export function SelectedRecord({ trip, onUse }: { trip: TripDetails; onUse: () => void }) {
  const record = toBusRecord(trip);

  return (
    <div className="flex flex-col gap-3.5 rounded-[1.25rem] border-[1.5px] border-crimson/25 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[0.95rem] font-extrabold">
          Selected record · {trip.busNumber} on {formatDay(trip.date)}
        </p>
        <Chip tone={STATUS_TONE[trip.verification]}>{trip.verification}</Chip>
      </div>

      <RecordFields record={record} />
      <VerificationNote record={record} />

      <div className="flex flex-wrap items-center gap-2.5">
        <PillButton onClick={() => void copyRecord(record)}>
          <Icon name="copy" />
          Copy details
        </PillButton>
        <PillButton primary onClick={onUse}>
          Use Details in Complaint
          <Icon name="send" />
        </PillButton>
      </div>
    </div>
  );
}
