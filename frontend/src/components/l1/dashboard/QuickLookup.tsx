"use client";

import { useState } from "react";
import { ChoiceGroup } from "@/components/dashboard/ChoiceGroup";
import { inputClass } from "@/components/dashboard/controls";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, PillButton } from "@/components/dashboard/ui";
import { lookupPermit, lookupVehicle, searchPeople } from "@/components/l1/entry/api";

const KINDS = ["Vehicle", "Permit", "Person"].map((value) => ({ value }));
type Kind = "Vehicle" | "Permit" | "Person";
type Row = { label: string; value: string };

const PERSON_TYPE: Record<string, string> = {
  driver: "Driver",
  conductor: "Conductor",
  owner: "Bus owner",
  sprpta_staff: "SPRPTA staff",
};

// Look a record up in the master data before entering a complaint (UC-L1-02): a vehicle by its number, a permit by
// its number, or a person by name.
export function QuickLookup({ className = "" }: { className?: string }) {
  const [kind, setKind] = useState<Kind>("Vehicle");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [rows, setRows] = useState<Row[] | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function search() {
    const term = query.trim();
    if (!term) return;
    setBusy(true);
    setMessage(null);
    setRows(null);
    if (kind === "Person") {
      const result = await searchPeople(term);
      if (!result.ok) setMessage(result.message);
      else if (result.data.length === 0) setMessage("No person on record matches that name.");
      else setRows(result.data.map((p) => ({ label: PERSON_TYPE[p.type] ?? p.type, value: p.name })));
    } else {
      const result = await (kind === "Vehicle" ? lookupVehicle(term) : lookupPermit(term));
      if (!result.ok) setMessage(result.message);
      else {
        const v = result.data;
        setRows([
          { label: "Transport", value: v.type === "bus" ? "Bus" : "Trishaw" },
          { label: "Vehicle number", value: v.number },
          { label: "Permit no.", value: v.permit ?? "Not on record" },
          { label: "Owner", value: v.owner ?? "Not on record" },
          { label: "Registered area", value: v.area },
          { label: "Past complaints", value: v.pastComplaints === 0 ? "None on record" : `${v.pastComplaints} on record` },
        ]);
      }
    }
    setBusy(false);
  }

  return (
    <Card className={className}>
      <CardHeading title="Quick lookup" subtitle="Check the records before you enter a complaint" />
      <ChoiceGroup
        label="Look up a"
        choices={KINDS}
        defaultValue="Vehicle"
        look="dark"
        onChange={([value]) => {
          setKind(value as Kind);
          setRows(null);
          setMessage(null);
        }}
      />
      <form
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          void search();
        }}
      >
        <label className="sr-only" htmlFor="lookup-query">
          {kind === "Person" ? "Name to look up" : `${kind} number to look up`}
        </label>
        <input
          id="lookup-query"
          className={inputClass}
          value={query}
          maxLength={kind === "Permit" ? 40 : 100}
          placeholder={kind === "Person" ? "Part of a name" : kind === "Permit" ? "For example GL-BP-0101" : "For example ND-7782"}
          onChange={(e) => setQuery(e.target.value)}
        />
        <PillButton primary className="!h-11" disabled={busy || query.trim() === ""} onClick={() => void search()}>
          Go
        </PillButton>
      </form>
      {message && <Note tone="neutral">{message}</Note>}
      {rows && (
        <dl className="m-0 flex flex-col gap-1.5">
          {rows.map((row, i) => (
            <div key={`${row.label}-${i}`} className="flex justify-between gap-3 rounded-xl bg-[#f7f4f5] px-3 py-2.5 text-[0.78rem]">
              <dt className="text-muted">{row.label}</dt>
              <dd className="m-0 font-extrabold">{row.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </Card>
  );
}
