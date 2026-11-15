"use client";

import { Field } from "@/components/dashboard/controls";
import { Chip, PillButton, muted } from "@/components/dashboard/ui";
import { PersonPicker } from "./PersonPicker";
import type { BusRecord, ComplaintFields, PersonType, TargetOption, VehicleRecord } from "./types";

const PERSON_TYPE: Record<string, PersonType | undefined> = {
  driver: "driver",
  conductor: "conductor",
  owner: "owner",
};

type Suggested = { id: number; name: string } | null;

// Who the complaint is against. The officer picks the kind of target; for a driver, conductor or owner the
// verified person is only offered, and nothing is recorded against them until the officer confirms it.
export function ComplaintTargetPicker({
  targets,
  values,
  record,
  vehicle,
  onTarget,
  onPerson,
}: {
  targets: TargetOption[];
  values: ComplaintFields;
  record: BusRecord | null;
  vehicle: VehicleRecord | null;
  onTarget: (target: TargetOption) => void;
  onPerson: (person: { id: number | null; name: string }) => void;
}) {
  const target = targets.find((t) => t.id === values.targetId) ?? null;

  function suggestion(): Suggested {
    if (!target) return null;
    if (target.code === "driver" || target.code === "conductor") {
      const on = record?.[target.code];
      return on && on.status === "verified" && on.personId !== null && on.name ? { id: on.personId, name: on.name } : null;
    }
    if (target.code === "owner") {
      const id = record?.ownerId ?? vehicle?.ownerId ?? null;
      const name = record?.owner ?? vehicle?.owner ?? null;
      return id !== null && name ? { id, name } : null;
    }
    return null;
  }

  const offered = suggestion();
  const confirmed = offered !== null && values.personId === offered.id;
  const kind = target?.code === "owner" ? "registered owner" : "verified person on duty";

  return (
    <div className="flex flex-col gap-3">
      <Field label="Who is the complaint against? *">
        <div role="group" aria-label="Who is the complaint against" className="flex flex-wrap gap-2">
          {targets.map((t) => {
            const on = t.id === values.targetId;
            return (
              <button
                key={t.id}
                type="button"
                aria-pressed={on}
                onClick={() => onTarget(t)}
                className={`focus-ring cursor-pointer rounded-full border-[1.5px] px-3.5 py-1.5 text-[0.78rem] font-bold transition-colors ${
                  on
                    ? "border-crimson bg-crimson text-white"
                    : "border-[#E5E7EB] bg-white text-slate-ink hover:border-crimson hover:text-crimson"
                }`}
              >
                {t.name}
              </button>
            );
          })}
        </div>
      </Field>

      {target && (target.code === "driver" || target.code === "conductor" || target.code === "owner") && (
        <>
          {offered ? (
            <div className="flex flex-wrap items-center gap-2 rounded-[1.1rem] bg-emerald-50 px-4 py-2.5 text-[0.78rem] text-emerald-900">
              <span>
                {kind === "registered owner" ? "Registered owner" : `Verified ${target.name.toLowerCase()} on duty`}:{" "}
                <b>{offered.name}</b>
              </span>
              {confirmed ? (
                <>
                  <Chip tone="ok">Confirmed as accused</Chip>
                  <PillButton onClick={() => onPerson({ id: null, name: "" })}>Not this person</PillButton>
                </>
              ) : (
                <PillButton onClick={() => onPerson({ id: offered.id, name: offered.name })}>
                  Confirm {offered.name} as the accused
                </PillButton>
              )}
            </div>
          ) : (
            <p className={muted}>
              {target.code === "owner"
                ? "No registered owner is on record for this bus."
                : `No verified ${target.name.toLowerCase()} is on record for this bus, so nobody is suggested.`}{" "}
              Search the directory, type a name, or leave it unknown.
            </p>
          )}
          {!confirmed && (
            <PersonPicker
              id="c-who"
              label="Accused person, if known"
              name={values.personName}
              personId={values.personId}
              personType={PERSON_TYPE[target.code]}
              placeholder="Unknown / unverified"
              hint="A person found in the directory is not verified for this trip unless the on-duty record says so."
              onChange={onPerson}
            />
          )}
        </>
      )}

      {target?.code === "bus_service" && (
        <p className={muted}>
          This complaint is about the bus, its route or the service, so no person is named. The bus and route above are the
          subject.
        </p>
      )}

      {target?.code === "other" && (
        <PersonPicker
          id="c-who"
          label="Person or party concerned, if any"
          name={values.personName}
          personId={values.personId}
          placeholder="Describe who or what the complaint is about"
          onChange={onPerson}
        />
      )}
    </div>
  );
}
