"use client";

import { Icon } from "@/components/dashboard/icons";
import { Chip, PillButton, muted } from "@/components/dashboard/ui";
import { copyRecord } from "@/components/l1/lookup/copy";
import { RecordFields, STATUS_TONE, VerificationNote } from "@/components/l1/lookup/RecordFields";
import type { BusRecord } from "./types";

// The verified record of the bus a complaint is about, read-only: Level 1 cannot edit it (only the System Admin
// maintains daily records). In the Quick Entry form the officer can copy it, change the bus, or search again; in
// a complaint that has left Level 1 it is shown with no actions.
export function SelectedBusDetails({
  record,
  busy = false,
  onChange,
  onSearch,
  heading = "Selected bus · filled in from the verified daily record",
}: {
  record: BusRecord;
  busy?: boolean;
  onChange?: () => void; // Change selected bus
  onSearch?: () => void; // search for another record
  heading?: string;
}) {
  return (
    <div className="flex flex-col gap-3.5 rounded-[1.25rem] border-[1.5px] border-emerald-200 bg-emerald-50/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="inline-flex items-center gap-1.5 text-[0.95rem] font-extrabold text-emerald-900">
          <Icon name="check" size={15} />
          {heading}
        </p>
        <Chip tone={STATUS_TONE[record.verification]}>{record.verification}</Chip>
      </div>

      <RecordFields record={record} />
      <VerificationNote record={record} />
      <p className={muted}>These details are read-only. Only the System Admin can change a daily record.</p>

      <div className="flex flex-wrap items-center gap-2.5">
        <PillButton onClick={() => void copyRecord(record)}>
          <Icon name="copy" />
          Copy details
        </PillButton>
        {onChange && (
          <PillButton disabled={busy} onClick={onChange}>
            Change selected bus
          </PillButton>
        )}
        {onSearch && (
          <PillButton disabled={busy} onClick={onSearch}>
            <Icon name="search" />
            Search bus
          </PillButton>
        )}
      </div>
    </div>
  );
}