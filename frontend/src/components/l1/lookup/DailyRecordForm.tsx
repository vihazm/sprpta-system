"use client";

import { useEffect, useRef, useState } from "react";
import { Field, inputClass, textareaClass } from "@/components/dashboard/controls";
import { Note } from "@/components/dashboard/Note";
import { Chip, PillButton, muted } from "@/components/dashboard/ui";
import { loadOptions, lookupVehicle } from "@/components/l1/entry/api";
import { PersonPicker } from "@/components/l1/entry/PersonPicker";
import type { RouteOption, VehicleRecord } from "@/components/l1/entry/types";
import { notify } from "@/lib/notify";
import { loadDailyRecord, saveDailyRecord, type DailyRecord, type DailyRecordFields, type PersonChoice } from "./records-api";

const none: PersonChoice = { id: null, name: "" };

function today() {
  return new Date().toLocaleDateString("en-CA"); // yyyy-mm-dd in the browser's own time zone
}

const blank = (): DailyRecordFields => ({
  date: today(),
  busNumber: "",
  routeId: null,
  departure: "",
  end: "",
  origin: "",
  destination: "",
  owner: none,
  driver: none,
  driverStart: "",
  driverEnd: "",
  conductor: none,
  conductorStart: "",
  conductorEnd: "",
  remarks: "",
});

function Step({ children }: { children: string }) {
  return <p className="text-[0.69rem] font-extrabold uppercase tracking-[0.09em] text-crimson">{children}</p>;
}

const when = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

// Add Daily Bus Record, or reopen one of the officer's own. A new record is saved as Pending Verification: nobody
// on it counts as verified and the lookup does not show it until System Admin approves and publishes it.
export function DailyRecordForm({
  recordId,
  onSaved,
  onClose,
}: {
  recordId?: number;
  onSaved: (record: DailyRecord) => void;
  onClose: () => void;
}) {
  const [routes, setRoutes] = useState<RouteOption[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [values, setValues] = useState<DailyRecordFields>(blank);
  const [saved, setSaved] = useState<DailyRecord | null>(null);
  const [vehicle, setVehicle] = useState<VehicleRecord | null>(null);
  const [vehicleMissing, setVehicleMissing] = useState(false);
  const [routeText, setRouteText] = useState("");
  const [busy, setBusy] = useState(false);
  const acting = useRef(false); // one save at a time, so a double click cannot send it twice

  useEffect(() => {
    let current = true;
    (async () => {
      const [lists, existing] = await Promise.all([loadOptions(), recordId ? loadDailyRecord(recordId) : null]);
      if (!current) return;
      if (!lists.ok) return setLoadError(lists.message);
      if (existing && !existing.ok) return setLoadError(existing.message);
      setRoutes(lists.data.routes);
      if (existing?.ok) {
        setSaved(existing.data);
        setValues(existing.data.fields);
        setRouteText(existing.data.route);
        const found = await lookupVehicle(existing.data.fields.busNumber);
        if (current && found.ok) setVehicle(found.data);
      }
    })();
    return () => {
      current = false;
    };
  }, [recordId]);

  const readOnly = saved !== null && !saved.editable;

  function set<K extends keyof DailyRecordFields>(key: K, value: DailyRecordFields[K]) {
    setValues((v) => ({ ...v, [key]: value }));
  }

  // The permit, office and registered owner come from the bus's own record, never from what is typed.
  async function checkBus() {
    const number = values.busNumber.trim();
    if (!number || vehicle) return;
    const result = await lookupVehicle(number);
    setVehicle(result.ok ? result.data : null);
    setVehicleMissing(!result.ok && result.status === 404);
    if (!result.ok) {
      if (result.status !== 404) notify.error("Could not check the bus", result.message);
      return;
    }
    const found = result.data;
    setValues((v) => ({ ...v, owner: v.owner.id === null && found.ownerId ? { id: found.ownerId, name: found.owner ?? "" } : v.owner }));
  }

  function chooseRoute(text: string) {
    setRouteText(text);
    const match = routes?.find((r) => r.name.toLowerCase() === text.trim().toLowerCase());
    set("routeId", match?.id ?? null);
  }

  // The form is checked here first; the server checks everything again and has the final say.
  function problem(): string | null {
    if (!values.date) return "Enter the operation date.";
    if (!values.busNumber.trim()) return "Enter the bus number.";
    if (!vehicle) return "Check the bus number: no bus on record matches it yet.";
    if (values.routeId === null) return "Choose a route from the list.";
    if (!values.departure) return "Enter the trip start time.";
    if (!values.origin.trim() || !values.destination.trim()) return "Enter the origin and the destination.";
    for (const [label, person] of [
      ["owner", values.owner],
      ["driver", values.driver],
      ["conductor", values.conductor],
    ] as const) {
      if (person.name.trim() && person.id === null) {
        return `Choose the ${label} from the matching records. A name that is not on record cannot be saved here.`;
      }
    }
    return null;
  }

  async function save() {
    if (acting.current) return;
    const wrong = problem();
    if (wrong) return notify.error("Check the form", wrong);
    acting.current = true;
    setBusy(true);
    try {
      const result = await saveDailyRecord(saved?.id ?? null, values);
      if (!result.ok) {
        // Everything typed stays in the form. A duplicate is a warning; anything else is the actual error.
        const title =
          result.status === 401 || result.status === 403
            ? "Not allowed"
            : result.status === 409
              ? "Possible duplicate"
              : "Could not save the record";
        return notify.error(title, result.message);
      }
      setSaved(result.data);
      notify.success(
        saved ? "Record updated" : "Record saved",
        `Record ${result.data.id} is ${result.data.statusLabel}. It is not shown in the lookup until Admin publishes it.`,
      );
      onSaved(result.data);
    } finally {
      acting.current = false;
      setBusy(false);
    }
  }

  if (loadError) return <Note tone="alert">{loadError}</Note>;
  if (!routes) return <p className={muted}>Loading the form…</p>;

  const places = routes.filter((r) => !vehicle || r.areaId === null || r.areaId === vehicle.areaId || r.id === values.routeId);
  const filledIn = `${inputClass} !bg-emerald-50`;
  const lock = readOnly ? { disabled: true } : {};

  return (
    <div className="flex flex-col gap-4">
      {readOnly && (
        <Note tone="neutral">
          This record is {saved?.statusLabel.toLowerCase()}, so it can no longer be changed. Only System Admin can
          change it now.
        </Note>
      )}

      <Step>Operation details</Step>
      <div className="grid gap-3.5 sm:grid-cols-3">
        <Field label="Operation date *" htmlFor="r-date">
          <input id="r-date" type="date" className={inputClass} value={values.date} max={today()} {...lock}
            onChange={(e) => set("date", e.target.value)} />
        </Field>
        <Field label="Bus number *" htmlFor="r-bus">
          <div className="relative">
            <input id="r-bus" className={`${inputClass} pr-[6rem]`} value={values.busNumber} {...lock}
              onChange={(e) => { set("busNumber", e.target.value); setVehicle(null); setVehicleMissing(false); }}
              onBlur={checkBus} />
            {(vehicle || vehicleMissing) && (
              <span className="absolute right-2 top-[0.55rem]">
                <Chip tone={vehicle ? "ok" : "warn"}>{vehicle ? "Found" : "Not found"}</Chip>
              </span>
            )}
          </div>
        </Field>
        <Field label="Permit number" htmlFor="r-permit">
          <input id="r-permit" readOnly className={vehicle ? filledIn : inputClass}
            value={vehicle?.permit ?? saved?.permit ?? ""} placeholder="Filled in from the bus" />
        </Field>
        <Field label="Route number / route *" htmlFor="r-route">
          <input id="r-route" list="r-routes" className={inputClass} value={routeText} {...lock}
            placeholder="Type to search the routes" onChange={(e) => chooseRoute(e.target.value)} />
          <datalist id="r-routes">
            {places.map((p) => <option key={p.id} value={p.name} />)}
          </datalist>
        </Field>
        <Field label="Origin *" htmlFor="r-origin">
          <input id="r-origin" className={inputClass} value={values.origin} {...lock}
            onChange={(e) => set("origin", e.target.value)} />
        </Field>
        <Field label="Destination *" htmlFor="r-destination">
          <input id="r-destination" className={inputClass} value={values.destination} {...lock}
            onChange={(e) => set("destination", e.target.value)} />
        </Field>
        <Field label="Office / district" htmlFor="r-area">
          <input id="r-area" readOnly className={vehicle ? filledIn : inputClass}
            value={vehicle?.area ?? saved?.area ?? ""} placeholder="Filled in from the bus" />
        </Field>
        <Field label="Trip start time *" htmlFor="r-start">
          <input id="r-start" type="time" className={inputClass} value={values.departure} {...lock}
            onChange={(e) => set("departure", e.target.value)} />
        </Field>
        <Field label="Trip end time" htmlFor="r-end">
          <input id="r-end" type="time" className={inputClass} value={values.end} {...lock}
            onChange={(e) => set("end", e.target.value)} />
        </Field>
      </div>
      {vehicleMissing && (
        <Note tone="alert">No bus on record has that number. A missing bus is added by the administrator.</Note>
      )}

      <Step>Owner details</Step>
      <div className="grid gap-3.5 sm:grid-cols-3">
        <PersonPicker id="r-owner" label="Registered owner" name={values.owner.name} personId={values.owner.id}
          personType="owner" placeholder="Search the owners"
          hint={vehicle ? "Filled in from the bus record. Change it only if the record states another owner." : undefined}
          onChange={(p) => !readOnly && set("owner", p)} />
      </div>
      <p className={muted}>
        Owner registration references and contact numbers are kept in the master records and are not shown or edited here.
      </p>

      <Step>Driver details</Step>
      <div className="grid gap-3.5 sm:grid-cols-3">
        <PersonPicker id="r-driver" label="Driver name" name={values.driver.name} personId={values.driver.id}
          personType="driver" placeholder="Search the drivers" onChange={(p) => !readOnly && set("driver", p)} />
        <Field label="Duty start time" htmlFor="r-dstart">
          <input id="r-dstart" type="time" className={inputClass} value={values.driverStart} {...lock}
            onChange={(e) => set("driverStart", e.target.value)} />
        </Field>
        <Field label="Duty end time" htmlFor="r-dend">
          <input id="r-dend" type="time" className={inputClass} value={values.driverEnd} {...lock}
            onChange={(e) => set("driverEnd", e.target.value)} />
        </Field>
      </div>

      <Step>Conductor details</Step>
      <div className="grid gap-3.5 sm:grid-cols-3">
        <PersonPicker id="r-conductor" label="Conductor name" name={values.conductor.name} personId={values.conductor.id}
          personType="conductor" placeholder="Search the conductors" onChange={(p) => !readOnly && set("conductor", p)} />
        <Field label="Duty start time" htmlFor="r-cstart">
          <input id="r-cstart" type="time" className={inputClass} value={values.conductorStart} {...lock}
            onChange={(e) => set("conductorStart", e.target.value)} />
        </Field>
        <Field label="Duty end time" htmlFor="r-cend">
          <input id="r-cend" type="time" className={inputClass} value={values.conductorEnd} {...lock}
            onChange={(e) => set("conductorEnd", e.target.value)} />
        </Field>
      </div>
      <p className={muted}>
        A person named here is <b>not</b> verified. System Admin verifies the driver and the conductor when approving the record.
      </p>

      <Step>Record details</Step>
      <Field label="Remarks" htmlFor="r-remarks">
        <textarea id="r-remarks" className={textareaClass} value={values.remarks} maxLength={1000} {...lock}
          onChange={(e) => set("remarks", e.target.value)} />
      </Field>
      <div className="grid gap-3.5 sm:grid-cols-3">
        <Field label="Entered by" htmlFor="r-by">
          <input id="r-by" readOnly className={inputClass} value={saved?.enteredBy ?? "You, when saved"} />
        </Field>
        <Field label="Created at" htmlFor="r-created">
          <input id="r-created" readOnly className={inputClass} value={saved ? when(saved.createdAt) : "When saved"} />
        </Field>
        <Field label="Verification status" htmlFor="r-status">
          <input id="r-status" readOnly className={inputClass} value={saved?.statusLabel ?? "Pending Verification"} />
        </Field>
      </div>

      <div className="flex flex-wrap items-center gap-2.5 border-t border-[#f1ebed] pt-3.5">
        {!readOnly && (
          <PillButton primary className="!h-11 !px-6" disabled={busy} onClick={save}>
            {saved ? "Save changes" : "Save Daily Record"}
          </PillButton>
        )}
        <PillButton disabled={busy} onClick={onClose}>
          {readOnly ? "Close" : "Cancel"}
        </PillButton>
      </div>
    </div>
  );
}
