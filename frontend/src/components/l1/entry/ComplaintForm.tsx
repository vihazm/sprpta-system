"use client";

import { useEffect, useRef, useState } from "react";
import { ChoiceGroup } from "@/components/dashboard/ChoiceGroup";
import { Field, inputClass, textareaClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { Note } from "@/components/dashboard/Note";
import { SEVERITY_COLOR, type Severity } from "@/components/dashboard/severity";
import { Chip, PillButton, muted } from "@/components/dashboard/ui";
import { FieldError } from "@/components/login/FieldError";
import { loadTrip, toBusRecord } from "@/components/l1/lookup/api";
import { BusLookupPanel } from "@/components/l1/lookup/BusLookupPanel";
import type { TripDetails } from "@/components/l1/lookup/types";
import { notify } from "@/lib/notify";
import { validateIdentifier } from "@/lib/validators";
import {
  decideDuplicate,
  forwardComplaint,
  keepIncomplete,
  loadComplaint,
  loadDuplicates,
  loadOptions,
  lookupVehicle,
  rejectComplaint,
  removeAttachment,
  saveComplaint,
  uploadAttachment,
} from "./api";
import { ComplaintTargetPicker } from "./ComplaintTargetPicker";
import { DuplicatePanel } from "./DuplicatePanel";
import { RejectPanel } from "./RejectPanel";
import { SelectedBusDetails } from "./SelectedBusDetails";
import type {
  BusRecord,
  ComplaintFields,
  DuplicateCandidate,
  DuplicateChoice,
  FormOptions,
  SavedComplaint,
  TargetOption,
  VehicleRecord,
} from "./types";

const TRANSPORT = ["Bus", "Trishaw"].map((value) => ({ value }));
const COMPLAINANT_TYPES = [
  { label: "Passenger", type: "passenger" },
  { label: "Driver", type: "driver" },
  { label: "Conductor", type: "conductor" },
  { label: "Owner", type: "owner" },
  { label: "Other", type: "other" },
] as const;
const REQUIRED_FIELDS = 10;

// Evidence the backend accepts, with the size limit of each kind (checked again on the server).
const MB = 1024 * 1024;
const FILE_TYPES = ".pdf,.jpg,.jpeg,.png,.webp,.mp3,.m4a,.wav,.ogg,.mp4,.webm,.mov,.txt,.eml";

// Fields filled in from the vehicle record are shown in green.
const filledIn = `${inputClass} !bg-emerald-50`;

const blank: ComplaintFields = {
  anonymous: false,
  name: "",
  mobile: "",
  email: "",
  date: "",
  mediumId: null,
  vehicleNumber: "",
  tripId: null,
  incidentTime: "",
  incidentLocation: "",
  complainantType: null,
  targetId: null,
  personId: null,
  personName: "",
  routeId: null,
  categoryId: null,
  severityId: null,
  subject: "",
  description: "",
};

function Step({ children }: { children: string }) {
  return <p className="text-[0.69rem] font-extrabold uppercase tracking-[0.09em] text-crimson">{children}</p>;
}

function today() {
  return new Date().toLocaleDateString("en-CA"); // yyyy-mm-dd in the browser's own time zone
}

function sizeLabel(bytes: number) {
  return bytes < MB ? `${Math.max(1, Math.round(bytes / 1024))} kB` : `${(bytes / MB).toFixed(1)} MB`;
}

function forwardBy(days: number) {
  return days === 0 ? "the same day" : `${days} day${days === 1 ? "" : "s"}`;
}

// Why a file cannot be attached, before it is sent: the server checks the type, size and contents again.
function fileProblem(file: File): string | null {
  const allowed = FILE_TYPES.split(",");
  if (!allowed.some((ext) => file.name.toLowerCase().endsWith(ext))) {
    return "Attach an image, a PDF, audio (MP3, M4A, WAV, OGG), video (MP4, WebM, MOV), a text file or an email.";
  }
  const limit = file.type.startsWith("video/") ? 50 * MB : file.type.startsWith("audio/") ? 25 * MB : 10 * MB;
  return file.size > limit ? `That file is over the ${limit / MB} MB limit for its kind.` : null;
}

// An error in the common popup. A session that ended, or a right the officer does not have, is said as such.
function fail(title: string, result: { message: string; status?: number }) {
  notify.error(result.status === 401 || result.status === 403 ? "Not allowed" : title, result.message);
}

// Entering a complaint that arrived by any medium (UC-L1-01 to UC-L1-10), all in one place. Used by the
// dashboard's Quick entry card and by the full New complaint page. Pass an id to continue a saved one, and/or
// a daily record (chosen in the Bus & Permit Lookup) to take the bus, permit, route, owner and incident date from it.
export function ComplaintForm({
  complaintId,
  tripId,
  layout = "page",
  onChanged,
  initialOptions,
}: {
  complaintId?: number;
  tripId?: number;
  initialOptions?: FormOptions; // the lists the form offers, read with the page; not used when continuing a saved case
  layout?: "page" | "quick"; // quick keeps the dashboard card's four numbered sections
  onChanged?: () => void; // called after something was saved or sent, so the page can refresh its numbers
}) {
  // A new complaint starts with the lists the page already loaded. One that continues a saved case or a daily record
  // waits for those too, so the form never shows empty before it is filled in.
  const seeded = complaintId || tripId ? undefined : initialOptions;
  const [options, setOptions] = useState<FormOptions | null>(seeded ?? null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [values, setValues] = useState<ComplaintFields>(blank);
  const [saved, setSaved] = useState<SavedComplaint | null>(null);
  const [vehicle, setVehicle] = useState<VehicleRecord | null>(null);
  const [vehicleMissing, setVehicleMissing] = useState(false);
  const [transport, setTransport] = useState("Bus");
  const [lookupOpen, setLookupOpen] = useState(false); // the Find bus panel inside the form
  const [record, setRecord] = useState<BusRecord | null>(null); // the verified daily record of the selected bus
  const [candidates, setCandidates] = useState<DuplicateCandidate[]>([]);
  const [busy, setBusy] = useState(false);
  const [finished, setFinished] = useState<SavedComplaint | null>(null);
  const [touched, setTouched] = useState({ mobile: false, email: false });
  const [formKey, setFormKey] = useState(0); // remounts the choice buttons after a reset or a load
  const saving = useRef<Promise<SavedComplaint | null> | null>(null);
  const requestId = useRef<string | null>(null); // one key per new complaint, so a retried save cannot make a second
  const acting = useRef(false); // one action at a time, so a double click or a retry cannot send it twice
  const filePicker = useRef<HTMLInputElement>(null);
  const vehicleBox = useRef<HTMLInputElement>(null);

  function show(complaint: SavedComplaint) {
    setSaved(complaint);
    setValues(complaint.values);
    setVehicle(complaint.vehicle);
    setRecord(complaint.duty);
    setFormKey((key) => key + 1);
  }

  // Takes the verified record as the form's bus. The record was read from the database by its id, so its
  // permit, owner and route are not typed in; whatever belonged to the previous bus is cleared first.
  async function applyTrip(trip: TripDetails, base: ComplaintFields) {
    const found = await lookupVehicle(trip.busNumber);
    setRecord(toBusRecord(trip));
    setTransport("Bus");
    setLookupOpen(false);
    setVehicle(found.ok ? found.data : null);
    setVehicleMissing(false);
    setCandidates([]);
    setValues({
      ...base,
      tripId: trip.id,
      date: trip.date,
      vehicleNumber: trip.busNumber,
      routeId: trip.routeId,
      personId: null,
      personName: "",
    });
    setFormKey((key) => key + 1);
    if (trip.verification === "Verified") {
      notify.success("Bus details added to the complaint", `${trip.busNumber}, trip at ${trip.departure}. Complete the rest of the form.`);
    } else {
      // Missing or unverified duty information is a problem to see, so it uses the error popup.
      notify.error(
        trip.verification === "Unverified" ? "Bus added, duty not verified" : "Bus added, duty unavailable",
        "Nobody on duty is named and nothing is guessed. Finish the details by hand or save it as incomplete.",
      );
    }
  }

  // Use Details in Complaint: the record is read from the backend again, so a record that was withdrawn since it
  // was selected is caught here and not at save time.
  async function adoptTrip(id: number) {
    const fresh = await loadTrip(id);
    if (!fresh.ok) return fail("That record is no longer available", fresh);
    await applyTrip(fresh.data, values);
  }

  useEffect(() => {
    let current = true;
    (async () => {
      const [lists, existing, trip] = await Promise.all([
        seeded ? { ok: true as const, data: seeded } : loadOptions(),
        complaintId ? loadComplaint(complaintId) : null,
        tripId ? loadTrip(tripId) : null,
      ]);
      if (!current) return;
      if (!lists.ok) return setLoadError(lists.message);
      if (existing && !existing.ok) return setLoadError(existing.message);
      setOptions(lists.data);

      if (existing?.ok) {
        show(existing.data);
        const found = await loadDuplicates(existing.data.id);
        if (current && found.ok) setCandidates(found.data);
      } else {
        setValues((v) => ({ ...v, date: today() }));
      }
      if (trip?.ok) await applyTrip(trip.data, existing?.ok ? existing.data.values : { ...blank, date: today() });
      else if (trip) fail("Could not use that record", trip);
    })();
    return () => {
      current = false;
    };
  }, [complaintId, tripId, seeded]);

  function set<K extends keyof ComplaintFields>(key: K, value: ComplaintFields[K]) {
    setValues((v) => ({ ...v, [key]: value }));
  }

  // ---------------------------------------------------------------- validation

  const mobileError = values.mobile.trim() ? validateIdentifier("phone", values.mobile) : "";
  const emailError = values.email.trim() ? validateIdentifier("email", values.email) : "";

  // The form is checked here first; the server checks everything again and has the final say.
  function valid() {
    setTouched({ mobile: true, email: true });
    if (!mobileError && !emailError) return true;
    notify.error("Check the form", "Fix the fields marked in red, then try again.");
    return false;
  }

  // ---------------------------------------------------------------- records and saving

  async function checkVehicle() {
    const number = values.vehicleNumber.trim();
    if (!number || vehicle) return; // already looked up; typing in the box clears it
    const result = await lookupVehicle(number);
    setVehicle(result.ok ? result.data : null);
    // Only a 404 means there is no such vehicle; any other failure (a timed-out session, no connection) is shown as it is.
    setVehicleMissing(!result.ok && result.status === 404);
    if (!result.ok && result.status !== 404) fail("Could not check the vehicle", result);
    if (result.ok) {
      setTransport(result.data.type === "trishaw" ? "Trishaw" : "Bus");
      const area = result.data.areaId;
      const routeOk = options?.routes.some((r) => r.id === values.routeId && (r.areaId === null || r.areaId === area));
      if (!routeOk) set("routeId", null);
      void findDuplicates(true);
    }
  }

  // Saves the form as a draft, or updates the saved one. Quiet saves stay silent when the form is not valid yet.
  function ensureSaved(quiet = false): Promise<SavedComplaint | null> {
    if (!saving.current) {
      saving.current = (async () => {
        if (saved === null) requestId.current ??= crypto.randomUUID();
        const result = await saveComplaint(saved?.id ?? null, values, requestId.current ?? undefined);
        if (!result.ok) {
          if (!quiet) fail("Could not save", result);
          return null;
        }
        setSaved(result.data);
        return result.data;
      })().finally(() => {
        saving.current = null;
      });
    }
    return saving.current;
  }

  // Runs one action at a time. Everything the officer entered stays in the form if it fails.
  async function once(action: () => Promise<void>) {
    if (acting.current) return;
    acting.current = true;
    setBusy(true);
    try {
      await action();
    } finally {
      acting.current = false;
      setBusy(false);
      onChanged?.();
    }
  }

  // Once the bus and the subject are known, the earlier complaints on that bus are listed.
  async function findDuplicates(busKnown = vehicle !== null) {
    if (!busKnown || !values.subject.trim()) return;
    const complaint = await ensureSaved(true);
    if (!complaint) return;
    const found = await loadDuplicates(complaint.id);
    if (found.ok) setCandidates(found.data);
  }

  async function chooseDuplicate(candidateId: number, choice: DuplicateChoice) {
    if (!saved) return;
    const result = await decideDuplicate(saved.id, candidateId, choice);
    if (!result.ok) return fail("Could not save the choice", result);
    setCandidates(result.data);
  }

  async function attach(file: File) {
    const problem = fileProblem(file);
    if (problem) return notify.error("Could not attach the file", problem);
    await once(async () => {
      const complaint = await ensureSaved();
      if (!complaint) return;
      const result = await uploadAttachment(complaint.id, file);
      if (!result.ok) return fail("Could not attach the file", result);
      setSaved((current) => current && { ...current, attachments: [...current.attachments, result.data] });
    });
  }

  async function detach(attachmentId: number) {
    if (!saved) return;
    const result = await removeAttachment(saved.id, attachmentId);
    if (!result.ok) return fail("Could not remove the file", result);
    setSaved({ ...saved, attachments: saved.attachments.filter((a) => a.id !== attachmentId) });
  }

  // ---------------------------------------------------------------- who the complaint is against

  // Choosing another target clears the accused person (it belonged to the old target) and any category that
  // is not approved for the new one. The server checks both again.
  function chooseTarget(target: TargetOption) {
    if (target.id === values.targetId) return;
    setValues((v) => {
      const category = options?.categories.find((c) => c.id === v.categoryId);
      const keep = !category || category.targetIds.length === 0 || category.targetIds.includes(target.id);
      return { ...v, targetId: target.id, personId: null, personName: "", categoryId: keep ? v.categoryId : null };
    });
  }

  // ---------------------------------------------------------------- the bus

  // Change selected bus: the previous bus's values go before another record (or a typed number) is used.
  function clearBus() {
    setValues((v) => ({
      ...v,
      tripId: null,
      vehicleNumber: "",
      routeId: null,
      personId: null,
      personName: "",
    }));
    setRecord(null);
    setVehicle(null);
    setVehicleMissing(false);
    setCandidates([]);
    setLookupOpen(false);
    setTimeout(() => vehicleBox.current?.focus(), 0);
  }

  // ---------------------------------------------------------------- the ways to finish

  async function saveDraft() {
    if (!valid()) return;
    await once(async () => {
      const complaint = await ensureSaved();
      if (!complaint) return;
      notify.success(
        complaint.reference ? "Changes saved" : "Draft saved",
        complaint.reference ? `${complaint.reference} stays incomplete.` : "It has no reference number yet.",
      );
    });
  }

  async function markIncomplete() {
    if (!valid()) return;
    await once(async () => {
      const complaint = await ensureSaved();
      if (!complaint) return;
      if (complaint.status === "incomplete") {
        return notify.success("Already incomplete", `${complaint.reference} is waiting for the missing details.`);
      }
      const result = await keepIncomplete(complaint.id);
      if (!result.ok) return fail("Could not keep it as incomplete", result);
      setSaved(result.data);
      notify.success("Kept as incomplete", `Reference ${result.data.reference} issued. The time-target clock is paused.`);
    });
  }

  async function checkDuplicates() {
    await once(async () => {
      const complaint = await ensureSaved();
      if (!complaint) return;
      const found = await loadDuplicates(complaint.id);
      if (!found.ok) return fail("Could not check for duplicates", found);
      setCandidates(found.data);
      notify.success(
        found.data.length ? "Possible duplicates found" : "No possible duplicates",
        found.data.length
          ? "Choose what each one is below."
          : "Nothing earlier on this bus looks like this complaint.",
      );
    });
  }

  async function forward() {
    if (!valid()) return;
    if (values.targetId === null) {
      return notify.error("Missing complaint target", "Choose who the complaint is against before forwarding it.");
    }
    await once(async () => {
      const complaint = await ensureSaved();
      if (!complaint) return;
      const result = await forwardComplaint(complaint.id);
      if (!result.ok) {
        const found = await loadDuplicates(complaint.id);
        if (found.ok) setCandidates(found.data);
        return fail("Cannot forward yet", result);
      }
      setFinished(result.data);
      notify.success("Complaint forwarded", `${result.data.reference} went to the ${result.data.area} area officer.`);
    });
  }

  async function reject(rejection: Parameters<typeof rejectComplaint>[1]) {
    await once(async () => {
      const complaint = await ensureSaved();
      if (!complaint) return;
      const result = await rejectComplaint(complaint.id, rejection);
      if (!result.ok) return fail("Cannot reject", result);
      setFinished(result.data);
      notify.success("Complaint rejected", "It is closed for good. Level 3 cannot reinstate it.");
    });
  }

  function startAnother() {
    setValues({ ...blank, date: today() });
    setSaved(null);
    setVehicle(null);
    setVehicleMissing(false);
    setCandidates([]);
    setFinished(null);
    setRecord(null);
    requestId.current = null;
    setLookupOpen(false);
    setTransport("Bus");
    setTouched({ mobile: false, email: false });
    setFormKey((key) => key + 1);
  }

  // ---------------------------------------------------------------- what is shown

  if (loadError) return <Note tone="alert">{loadError}</Note>;
  if (!options) return <p className={muted}>Loading the form…</p>;

  if (saved && saved.status !== "draft" && saved.status !== "incomplete" && !finished) {
    return (
      <div className="flex flex-col gap-4">
        <Note tone="neutral">
          This complaint has already been forwarded or rejected, so it can no longer be changed.
        </Note>
        <p className="text-[0.88rem] font-bold">
          {saved.reference ?? "No reference number"} · {saved.values.subject || "No subject"}
        </p>
        <p className={muted}>
          Against <b>{saved.targetName ?? "not classified"}</b>
          {saved.values.personName && <> · {saved.values.personName}</>} · Issue <b>{saved.categoryName ?? "none"}</b>
        </p>
        {saved.duty ? (
          <SelectedBusDetails record={saved.duty} heading="Selected bus · saved with this complaint" />
        ) : (
          <p className={muted}>No verified bus record was linked to this complaint.</p>
        )}
      </div>
    );
  }

  if (finished) {
    const forwarded = finished.status === "forwarded";
    return (
      <div className="flex flex-col gap-3 rounded-[1.25rem] bg-emerald-50 px-5 py-4 text-emerald-900">
        <p className="inline-flex items-center gap-1.5 text-[0.95rem] font-extrabold">
          <Icon name="check" size={16} />
          {forwarded ? "Complaint forwarded" : "Complaint rejected"}
        </p>
        <p className="text-[0.81rem] leading-[1.5]">
          {forwarded ? (
            <>
              Reference <b>{finished.reference}</b> is now with the {finished.area} area officer, {finished.officer}.
              {(finished.values.mobile || finished.values.email) &&
                " The registration message is not sent yet, because messaging is not set up."}
            </>
          ) : (
            <>
              {finished.reference ? <b>{finished.reference}</b> : "This case had no reference number"} is rejected and
              final. Nothing was merged or deleted.
            </>
          )}
        </p>
        <PillButton className="self-start" onClick={startAnother}>
          Enter another complaint
        </PillButton>
      </div>
    );
  }

  const places = options.routes.filter(
    (r) => !vehicle || r.areaId === null || r.areaId === vehicle.areaId || r.id === values.routeId,
  );
  // A category with no approved targets is open to all; otherwise it shows only under its targets.
  const categories = options.categories.filter(
    (c) =>
      values.targetId === null ||
      c.targetIds.length === 0 ||
      c.targetIds.includes(values.targetId) ||
      c.id === values.categoryId,
  );
  const severityFor = (name: string) => SEVERITY_COLOR[name.toLowerCase() as Severity];
  const done = [
    values.anonymous || values.name.trim() !== "",
    values.date !== "",
    values.mediumId !== null,
    vehicle !== null,
    values.routeId !== null,
    values.targetId !== null,
    values.categoryId !== null,
    values.severityId !== null,
    values.subject.trim() !== "",
    values.description.trim() !== "",
  ].filter(Boolean).length;
  const markedDuplicate = candidates.find((c) => c.choice === "duplicate_of")?.reference ?? "";
  const medium = options.mediums.find((m) => m.id === values.mediumId)?.name ?? "";
  const severity = options.severities.find((s) => s.id === values.severityId)?.name ?? "";
  const status = saved ? (saved.reference ? `Incomplete, ${saved.reference}` : "Draft saved") : "Not saved yet";

  const quick = layout === "quick";
  const titles = quick
    ? { bus: "2 · Which transport and who", complainant: "1 · Who sent it and how", complaint: "3 · Complaint information", review: "4 · Review and actions" }
    : { bus: "A · Bus and incident details", complainant: "B · Complainant", complaint: "C · Complaint", review: "E · Review and actions" };

  // ------------------------------------------------ the bus (and the verified daily record)
  const busSection = (
    <>
      <Step>{titles.bus}</Step>
      {lookupOpen && (
        <div className="flex flex-col gap-3 rounded-[1.25rem] border-[1.5px] border-crimson/25 p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-[0.95rem] font-extrabold">Find bus · Bus &amp; permit lookup</p>
            <PillButton onClick={() => setLookupOpen(false)}>
              <Icon name="close" size={12} />
              Close
            </PillButton>
          </div>
          <BusLookupPanel
            initialDate={values.date}
            initialBus={values.vehicleNumber}
            hint="Use Details in Complaint fills this form from the verified record and closes the lookup."
            onUse={(trip) => void adoptTrip(trip.id)}
          />
        </div>
      )}
      {record ? (
        <SelectedBusDetails record={record} busy={busy} onChange={clearBus} onSearch={() => setLookupOpen(true)} />
      ) : (
        <>
          <div className="grid gap-3.5 sm:grid-cols-3">
            <Field label="Transport">
              <ChoiceGroup
                key={transport}
                label="Transport"
                choices={TRANSPORT}
                defaultValue={transport}
                onChange={([kind]) => {
                  setTransport(kind);
                  if (vehicle && vehicle.type !== kind.toLowerCase()) {
                    setVehicle(null);
                    set("vehicleNumber", "");
                  }
                }}
              />
            </Field>
            <Field label="Vehicle number *" htmlFor="c-vehicle">
              <div className="relative">
                <input
                  id="c-vehicle"
                  ref={vehicleBox}
                  className={`${inputClass} pr-[6rem]`}
                  value={values.vehicleNumber}
                  onChange={(e) => {
                    set("vehicleNumber", e.target.value);
                    setVehicle(null);
                    setVehicleMissing(false);
                  }}
                  onBlur={checkVehicle}
                />
                {(vehicle || vehicleMissing) && (
                  <span className="absolute right-2 top-[0.55rem]">
                    <Chip tone={vehicle ? "ok" : "warn"}>{vehicle ? "Found" : "Not found"}</Chip>
                  </span>
                )}
              </div>
            </Field>
            <Field label="Incident date *" htmlFor="c-date">
              <input
                id="c-date"
                type="date"
                className={inputClass}
                value={values.date}
                onChange={(e) => set("date", e.target.value)}
              />
            </Field>
          </div>
          <div className="grid gap-3.5 sm:grid-cols-3">
            <Field label="Route or stand *" htmlFor="c-route">
              <select
                id="c-route"
                className={vehicle ? filledIn : inputClass}
                value={values.routeId ?? ""}
                onChange={(e) => set("routeId", e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">Choose a route or stand</option>
                {places.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Area" htmlFor="c-area">
              <input
                id="c-area"
                readOnly
                className={vehicle ? filledIn : inputClass}
                value={vehicle ? `${vehicle.area} (from the vehicle)` : ""}
                placeholder="Filled in from the vehicle"
              />
            </Field>
            <div className="flex flex-col justify-end gap-1.5">
              {transport === "Bus" ? (
                <PillButton className="!h-11 justify-start" disabled={busy} onClick={() => setLookupOpen(true)}>
                  <Icon name="search" />
                  Find bus
                </PillButton>
              ) : (
                <p className={muted}>Trishaws have no daily trip records. Enter the number and the route by hand.</p>
              )}
            </div>
          </div>
          {transport === "Bus" && (
            <p className={muted}>
              Find bus looks up the verified trip, permit, owner, driver and conductor for the incident date and fills them
              in here. A bus typed by hand is not verified, so no one on duty is named.
            </p>
          )}
          {vehicle && (
            <div
              className={`flex flex-wrap items-center gap-x-5 gap-y-2 rounded-[1.1rem] px-4 py-3 text-[0.78rem] ${
                vehicle.permit ? "bg-emerald-50 text-emerald-900" : "bg-amber-50 text-amber-900"
              }`}
            >
              <b className="inline-flex items-center gap-1.5 font-extrabold">
                <Icon name="check" size={14} />
                {vehicle.permit ? "Vehicle found, permit valid" : "Vehicle found, no valid permit on record"}
              </b>
              {vehicle.permit && (
                <span>
                  Permit <b>{vehicle.permit}</b>
                </span>
              )}
              <span>
                Owner <b>{vehicle.owner ?? "not on record"}</b>
              </span>
              <span>
                Registered area <b>{vehicle.area}</b>
              </span>
              <span>
                Past complaints <b>{vehicle.pastComplaints}</b>
              </span>
            </div>
          )}
          {vehicleMissing && (
            <Note tone="alert">
              No vehicle on record has that number. Check the number and try again. A missing record is added by the
              administrator. Until then the complaint can be saved as incomplete.
            </Note>
          )}
        </>
      )}
    </>
  );

  // ------------------------------------------------ who complained
  const complainantSection = (
    <>
      <Step>{titles.complainant}</Step>
      <div className="grid gap-3.5 sm:grid-cols-3">
        <div className="flex flex-col gap-2">
          <Field label="Complainant name *" htmlFor="c-name">
            <input
              id="c-name"
              className={inputClass}
              value={values.name}
              disabled={values.anonymous}
              onChange={(e) => set("name", e.target.value)}
            />
          </Field>
          <label className="flex items-center gap-2 text-[0.75rem] text-slate-600">
            <input
              type="checkbox"
              className="accent-crimson"
              checked={values.anonymous}
              onChange={(e) => {
                setValues((v) => ({ ...v, anonymous: e.target.checked, name: "", mobile: "", email: "" }));
                setTouched({ mobile: false, email: false });
              }}
            />
            Anonymous complaint, no name and no contact
          </label>
        </div>
        <Field label="Mobile number" htmlFor="c-mobile">
          <input
            id="c-mobile"
            type="tel"
            className={inputClass}
            value={values.mobile}
            disabled={values.anonymous}
            aria-invalid={touched.mobile && mobileError !== ""}
            onChange={(e) => set("mobile", e.target.value)}
            onBlur={() => setTouched((t) => ({ ...t, mobile: true }))}
          />
          {touched.mobile && mobileError ? (
            <FieldError id="c-mobile-error" message={mobileError} />
          ) : (
            <p className={muted}>Optional. Messages are sent only when a contact is recorded.</p>
          )}
        </Field>
        <Field label="Email address" htmlFor="c-email">
          <input
            id="c-email"
            type="email"
            className={inputClass}
            value={values.email}
            disabled={values.anonymous}
            aria-invalid={touched.email && emailError !== ""}
            onChange={(e) => set("email", e.target.value)}
            onBlur={() => setTouched((t) => ({ ...t, email: true }))}
          />
          {touched.email && emailError ? (
            <FieldError id="c-email-error" message={emailError} />
          ) : (
            <p className={muted}>Optional.</p>
          )}
        </Field>
      </div>
      <Field label="Complainant type">
        <ChoiceGroup
          label="Complainant type"
          choices={COMPLAINANT_TYPES.map((c) => ({ value: c.label }))}
          defaultValue={COMPLAINANT_TYPES.find((c) => c.type === values.complainantType)?.label ?? ""}
          onChange={([label]) => set("complainantType", COMPLAINANT_TYPES.find((c) => c.label === label)?.type ?? null)}
        />
      </Field>
      <Field label="Complaint medium *">
        <ChoiceGroup
          label="Medium"
          choices={options.mediums.map((m) => ({ value: m.name }))}
          defaultValue={medium}
          onChange={([name]) => set("mediumId", options.mediums.find((m) => m.name === name)?.id ?? null)}
        />
      </Field>
    </>
  );

  // ------------------------------------------------ the complaint
  const complaintSection = (
    <>
      <Step>{titles.complaint}</Step>
      <ComplaintTargetPicker
        targets={options.targets}
        values={values}
        record={record}
        vehicle={vehicle}
        onTarget={chooseTarget}
        onPerson={(person) => setValues((v) => ({ ...v, personId: person.id, personName: person.name }))}
      />
      <div className="grid gap-3.5 sm:grid-cols-3">
        <Field label="Subject *" htmlFor="c-subject">
          <input
            id="c-subject"
            className={inputClass}
            value={values.subject}
            onChange={(e) => set("subject", e.target.value)}
            onBlur={() => findDuplicates()}
          />
        </Field>
        <Field label="Issue category *" htmlFor="c-category">
          <select
            id="c-category"
            className={inputClass}
            value={values.categoryId ?? ""}
            onChange={(e) => set("categoryId", e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Choose a category</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Incident time" htmlFor="c-time">
          <input
            id="c-time"
            type="time"
            className={inputClass}
            value={values.incidentTime}
            onChange={(e) => set("incidentTime", e.target.value)}
          />
          <p className={muted}>{record ? `Only if it differs from the trip time, ${record.departure}.` : "Optional."}</p>
        </Field>
      </div>
      <div className="grid gap-3.5 sm:grid-cols-3">
        <Field label="Incident location" htmlFor="c-location">
          <input
            id="c-location"
            className={inputClass}
            value={values.incidentLocation}
            placeholder="For example Galle bus stand"
            onChange={(e) => set("incidentLocation", e.target.value)}
          />
        </Field>
      </div>
      <Field label="Severity *">
        <ChoiceGroup
          label="Severity"
          choices={options.severities.map((s) => ({ value: s.name, dot: severityFor(s.name) }))}
          defaultValue={severity}
          look="dark"
          onChange={([name]) => set("severityId", options.severities.find((s) => s.name === name)?.id ?? null)}
        />
        <p className={muted}>
          Forward by: {options.severities.map((s) => `${s.name} ${forwardBy(s.forwardDays)}`).join(" · ")}. The clock
          starts at registration.
        </p>
      </Field>
      <Field label="Complaint description *" htmlFor="c-description">
        <textarea
          id="c-description"
          className={textareaClass}
          value={values.description}
          onChange={(e) => set("description", e.target.value)}
        />
      </Field>
    </>
  );

  // ------------------------------------------------ evidence
  const evidenceSection = (
    <>
      {!quick && <Step>D · Evidence</Step>}
      <div className="flex flex-col gap-2.5">
        <input
          ref={filePicker}
          type="file"
          accept={FILE_TYPES}
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) void attach(file);
          }}
        />
        <div className="flex flex-wrap items-center gap-2.5">
          <PillButton className="!h-11 !border-dashed" disabled={busy} onClick={() => filePicker.current?.click()}>
            <Icon name="attach" />
            Attach evidence
          </PillButton>
          <span className={muted}>
            Images and PDFs up to 10 MB, audio (MP3, M4A, WAV, OGG) up to 25 MB, video (MP4, WebM, MOV) up to 50 MB.
          </span>
        </div>
        {saved && saved.attachments.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {saved.attachments.map((file) => (
              <Chip key={file.id}>
                {file.name} · {sizeLabel(file.size)}
                <button
                  type="button"
                  onClick={() => detach(file.id)}
                  aria-label={`Remove ${file.name}`}
                  className="focus-ring cursor-pointer rounded-full text-slate-500 hover:text-crimson"
                >
                  <Icon name="close" size={11} />
                </button>
              </Chip>
            ))}
          </div>
        )}
      </div>
    </>
  );

  // ------------------------------------------------ duplicates, review and actions
  const reviewSection = (
    <>
      <Step>{titles.review}</Step>
      <DuplicatePanel candidates={candidates} onChoose={chooseDuplicate} />

      <p className={muted}>
        {status} · {done} of {REQUIRED_FIELDS} required fields done
      </p>
      <div className="flex flex-wrap items-center gap-2.5">
        <PillButton disabled={busy} onClick={saveDraft}>
          {saved?.reference ? "Save changes" : "Save draft"}
        </PillButton>
        <PillButton className="!border-amber-200 !text-amber-900" disabled={busy} onClick={markIncomplete}>
          Save as incomplete
        </PillButton>
        <PillButton disabled={busy} onClick={checkDuplicates}>
          <Icon name="copy" />
          Check duplicates
        </PillButton>
        <span className={muted}>A draft has no reference number yet. Incomplete issues one and pauses the clock.</span>
      </div>

      <RejectPanel suggestedEarlier={markedDuplicate} busy={busy} onReject={reject} />

      <div className="flex flex-wrap items-center justify-between gap-3.5 border-t border-[#f1ebed] pt-3.5">
        <p className={`${muted} max-w-[26rem]`}>
          Saving a draft or as incomplete never forwards the complaint. A reference number is issued when you forward.
          A registration message goes to the complainant if a contact is on record, once messaging is set up.
        </p>
        <PillButton primary className="!h-11 !px-6" disabled={busy} onClick={forward}>
          Forward to {vehicle ? `${vehicle.area} ` : ""}area officer
          <Icon name="send" />
        </PillButton>
      </div>
    </>
  );

  return (
    <div key={formKey} className="flex flex-col gap-4">
      <p className={muted}>
        <span className="font-bold text-crimson">*</span> needed before the complaint can be forwarded. A draft or an
        incomplete complaint can be saved without them.
      </p>
      {quick ? (
        <>
          {complainantSection}
          {busSection}
          {complaintSection}
          {evidenceSection}
          {reviewSection}
        </>
      ) : (
        <>
          {busSection}
          {complainantSection}
          {complaintSection}
          {evidenceSection}
          {reviewSection}
        </>
      )}
    </div>
  );
}
