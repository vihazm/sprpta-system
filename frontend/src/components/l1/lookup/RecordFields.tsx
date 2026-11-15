import type { ReactNode } from "react";
import { Chip, eyebrow, muted } from "@/components/dashboard/ui";
import type { BusRecord } from "@/components/l1/entry/types";
import { formatDay, routeNumber } from "./format";
import type { DutyPerson } from "./types";

export const STATUS_TONE = { Verified: "ok", Unverified: "warn", Unavailable: "info" } as const;

// What a person is shown as: their name once verified, otherwise the reason there is no name.
export function staffText(p: DutyPerson) {
  return p.status === "verified" ? (p.name ?? "Unavailable") : p.status === "unverified" ? "Unverified" : "Unavailable";
}

function Value({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 rounded-[1.1rem] bg-[#faf6f7] px-4 py-3">
      <p className={eyebrow}>{label}</p>
      <div className="text-[0.92rem] font-extrabold text-ink">{children}</div>
    </div>
  );
}

function Person({ person }: { person: DutyPerson }) {
  return person.status === "verified" ? (
    <>{person.name}</>
  ) : (
    <Chip tone={person.status === "unverified" ? "warn" : "info"}>{staffText(person)}</Chip>
  );
}

/** The verified record's values, read-only. Shared by the lookup page and the complaint form. */
export function RecordFields({ record }: { record: BusRecord }) {
  const number = routeNumber(record.route);
  return (
    <div className="grid gap-3 sm:grid-cols-2 min-[1200px]:grid-cols-3">
      <Value label="Incident date">{formatDay(record.date)}</Value>
      <Value label="Bus number">{record.busNumber}</Value>
      <Value label="Permit number">{record.permitNumber}</Value>
      <Value label="Route number">{number ?? <Chip tone="info">Not stated</Chip>}</Value>
      <Value label="Route">{record.route}</Value>
      <Value label="Trip time">{record.departure}</Value>
      <Value label="Origin">{record.origin}</Value>
      <Value label="Destination">{record.destination}</Value>
      <Value label="Registered owner">{record.owner ?? <Chip tone="info">Unavailable</Chip>}</Value>
      <Value label="Driver on duty">
        <Person person={record.driver} />
      </Value>
      <Value label="Conductor on duty">
        <Person person={record.conductor} />
      </Value>
      <Value label="Operation status">
        {record.tripStatus === "cancelled" ? (
          <Chip tone="warn">Cancelled</Chip>
        ) : record.tripStatus === "partial" ? (
          <Chip tone="warn">Stopped early</Chip>
        ) : (
          <Chip tone="ok">Completed</Chip>
        )}
      </Value>
      <Value label="Verification status">
        <Chip tone={STATUS_TONE[record.verification]}>{record.verification}</Chip>
      </Value>
      <Value label="Record source">
        {record.synthetic ? <Chip tone="info">Simulated test data, not an official record</Chip> : "Published daily record"}
      </Value>
    </div>
  );
}

export function VerificationNote({ record }: { record: BusRecord }) {
  if (record.verification === "Verified") return null;
  return (
    <p className={muted}>
      Only people verified by the System Admin are named. Nothing is guessed, so an unverified or missing person stays
      out of the complaint. Finish the details by hand, or keep the complaint as incomplete.
    </p>
  );
}

/** The record as readable text, for Copy Details. */
export function recordSummary(r: BusRecord) {
  return [
    `Incident date: ${formatDay(r.date)}`,
    `Bus number: ${r.busNumber}`,
    `Permit number: ${r.permitNumber}`,
    `Route number: ${routeNumber(r.route) ?? "Not stated"}`,
    `Route: ${r.route}`,
    `Trip time: ${r.departure}`,
    `Origin: ${r.origin}`,
    `Destination: ${r.destination}`,
    `Registered owner: ${r.owner ?? "Unavailable"}`,
    `Driver on duty: ${staffText(r.driver)}`,
    `Conductor on duty: ${staffText(r.conductor)}`,
    `Operation status: ${r.tripStatus === "cancelled" ? "Cancelled" : r.tripStatus === "partial" ? "Stopped early" : "Completed"}`,
    `Verification status: ${r.verification}`,
    `Record source: ${r.synthetic ? "Simulated test data, not an official record" : "Published daily record"}`,
  ].join("\n");
}