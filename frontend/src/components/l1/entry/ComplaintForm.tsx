"use client";

import { useEffect, useRef, useState } from "react";
import { ChoiceGroup } from "@/components/dashboard/ChoiceGroup";
import { Field, inputClass, textareaClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { Note } from "@/components/dashboard/Note";
import { SEVERITY_COLOR, type Severity } from "@/components/dashboard/severity";
import { Chip, PillButton, muted } from "@/components/dashboard/ui";
import { notify } from "@/lib/notify";
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
import { DuplicatePanel } from "./DuplicatePanel";
import { PersonPicker } from "./PersonPicker";
import { RejectPanel } from "./RejectPanel";
import type {
  ComplaintFields,
  DuplicateCandidate,
  DuplicateChoice,
  FormOptions,
  PersonType,
  SavedComplaint,
  VehicleRecord,
} from "./types";

const TRANSPORT = ["Bus", "Trishaw"].map((value) => ({ value }));
const ABOUT: { label: string; type: PersonType }[] = [
  { label: "Driver", type: "driver" },
  { label: "Conductor", type: "conductor" },
  { label: "SPRPTA staff", type: "sprpta_staff" },
];
const REQUIRED_FIELDS = 9;

// Fields filled in from the vehicle record are shown in green.
const filledIn = `${inputClass} !bg-emerald-50`;

const blank: ComplaintFields = {
  anonymous: false,
  name: "",
  contact: "",
  date: "",
  mediumId: null,
  vehicleNumber: "",
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
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} kB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function forwardBy(days: number) {
  return days === 0 ? "the same day" : `${days} day${days === 1 ? "" : "s"}`;
}

// Entering a complaint that arrived by any medium (UC-L1-01 to UC-L1-10), all in one place. Used by the
// dashboard's Quick entry card and by the full New complaint page; pass an id to continue a saved one.
export function ComplaintForm({ complaintId }: { complaintId?: number }) {
  const [options, setOptions] = useState<FormOptions | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [values, setValues] = useState<ComplaintFields>(blank);
  const [saved, setSaved] = useState<SavedComplaint | null>(null);
  const [vehicle, setVehicle] = useState<VehicleRecord | null>(null);
  const [vehicleMissing, setVehicleMissing] = useState(false);
  const [about, setAbout] = useState(ABOUT[0]);
  const [candidates, setCandidates] = useState<DuplicateCandidate[]>([]);
  const [busy, setBusy] = useState(false);
  const [finished, setFinished] = useState<SavedComplaint | null>(null);
  const [formKey, setFormKey] = useState(0); // remounts the choice buttons after a reset or a load
  const saving = useRef<Promise<SavedComplaint | null> | null>(null);
  const filePicker = useRef<HTMLInputElement>(null);

  function show(complaint: SavedComplaint) {
    setSaved(complaint);
    setValues(complaint.values);
    setVehicle(complaint.vehicle);
    setFormKey((key) => key + 1);
  }

  useEffect(() => {
    let current = true;
    (async () => {
      const [lists, existing] = await Promise.all([loadOptions(), complaintId ? loadComplaint(complaintId) : null]);
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
    })();
    return () => {
      current = false;
    };
  }, [complaintId]);

  function set<K extends keyof ComplaintFields>(key: K, value: ComplaintFields[K]) {
    setValues((v) => ({ ...v, [key]: value }));
  }

  // ---------------------------------------------------------------- records and saving

  async function checkVehicle() {
    const number = values.vehicleNumber.trim();
    if (!number) return;
    if (vehicle) return; // already looked up; typing in the box clears it
    const result = await lookupVehicle(number);
    setVehicle(result.ok ? result.data : null);
    setVehicleMissing(!result.ok);
    if (result.ok) {
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
        const result = await saveComplaint(saved?.id ?? null, values);
        if (!result.ok) {
          if (!quiet) notify.error("Could not save", result.message);
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

  // Once the vehicle and the subject are known, the earlier complaints on that vehicle are listed.
  async function findDuplicates(vehicleFound = vehicle !== null) {
    if (!vehicleFound || !values.subject.trim()) return;
    const complaint = await ensureSaved(true);
    if (!complaint) return;
    const found = await loadDuplicates(complaint.id);
    if (found.ok) setCandidates(found.data);
  }

  async function chooseDuplicate(candidateId: number, choice: DuplicateChoice) {
    if (!saved) return;
    const result = await decideDuplicate(saved.id, candidateId, choice);
    if (!result.ok) return notify.error("Could not save the choice", result.message);
    setCandidates(result.data);
  }

  async function attach(file: File) {
    setBusy(true);
    const complaint = await ensureSaved();
    const result = complaint ? await uploadAttachment(complaint.id, file) : null;
    setBusy(false);
    if (result === null) return;
    if (!result.ok) return notify.error("Could not attach the file", result.message);
    setSaved((current) => current && { ...current, attachments: [...current.attachments, result.data] });
  }

  async function detach(attachmentId: number) {
    if (!saved) return;
    const result = await removeAttachment(saved.id, attachmentId);
    if (!result.ok) return notify.error("Could not remove the file", result.message);
    setSaved({ ...saved, attachments: saved.attachments.filter((a) => a.id !== attachmentId) });
  }

  // ---------------------------------------------------------------- the four ways to finish

  async function saveDraft() {
    setBusy(true);
    const complaint = await ensureSaved();
    setBusy(false);
    if (!complaint) return;
    notify.success(
      complaint.reference ? "Changes saved" : "Draft saved",
      complaint.reference ? `${complaint.reference} stays incomplete.` : "It has no reference number yet.",
    );
  }

  async function markIncomplete() {
    setBusy(true);
    const complaint = await ensureSaved();
    if (!complaint) return setBusy(false);
    if (complaint.status === "incomplete") {
      setBusy(false);
      return notify.success("Already incomplete", `${complaint.reference} is waiting for the missing details.`);
    }
    const result = await keepIncomplete(complaint.id);
    setBusy(false);
    if (!result.ok) return notify.error("Could not keep it as incomplete", result.message);
    setSaved(result.data);
    notify.success("Kept as incomplete", `Reference ${result.data.reference} issued. The time-target clock is paused.`);
  }

  async function forward() {
    setBusy(true);
    const complaint = await ensureSaved();
    if (!complaint) return setBusy(false);
    const result = await forwardComplaint(complaint.id);
    if (!result.ok) {
      const found = await loadDuplicates(complaint.id);
      if (found.ok) setCandidates(found.data);
      setBusy(false);
      return notify.error("Cannot forward yet", result.message);
    }
    setBusy(false);
    setFinished(result.data);
    notify.success("Complaint forwarded", `${result.data.reference} went to the ${result.data.area} area officer.`);
  }

  async function reject(rejection: Parameters<typeof rejectComplaint>[1]) {
    setBusy(true);
    const complaint = await ensureSaved();
    if (!complaint) return setBusy(false);
    const result = await rejectComplaint(complaint.id, rejection);
    setBusy(false);
    if (!result.ok) return notify.error("Cannot reject", result.message);
    setFinished(result.data);
    notify.success("Complaint rejected", "It is closed for good. Level 3 cannot reinstate it.");
  }

  function startAnother() {
    setValues({ ...blank, date: today() });
    setSaved(null);
    setVehicle(null);
    setVehicleMissing(false);
    setCandidates([]);
    setFinished(null);
    setAbout(ABOUT[0]);
    setFormKey((key) => key + 1);
  }

  // ---------------------------------------------------------------- what is shown

  if (loadError) return <Note tone="alert">{loadError}</Note>;
  if (!options) return <p className={muted}>Loading the form…</p>;

  if (saved && saved.status !== "draft" && saved.status !== "incomplete" && !finished) {
    return (
      <Note tone="neutral">
        This complaint has already been forwarded or rejected, so it can no longer be changed.
      </Note>
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
              {finished.values.contact && " The registration message is not sent yet, because messaging is not set up."}
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

  const places = options.routes.filter((r) => !vehicle || r.areaId === null || r.areaId === vehicle.areaId);
  const severityFor = (name: string) => SEVERITY_COLOR[name.toLowerCase() as Severity];
  const done = [
    values.anonymous || values.name.trim() !== "",
    values.date !== "",
    values.mediumId !== null,
    vehicle !== null,
    values.routeId !== null,
    values.categoryId !== null,
    values.severityId !== null,
    values.subject.trim() !== "",
    values.description.trim() !== "",
  ].filter(Boolean).length;
  const markedDuplicate = candidates.find((c) => c.choice === "duplicate_of")?.reference ?? "";
  const medium = options.mediums.find((m) => m.id === values.mediumId)?.name ?? "";
  const severity = options.severities.find((s) => s.id === values.severityId)?.name ?? "";
  const status = saved ? (saved.reference ? `Incomplete, ${saved.reference}` : "Draft saved") : "Not saved yet";

  return (
    <div key={formKey} className="flex flex-col gap-4">
      <Step>1 · Who sent it and how</Step>
      <div className="grid gap-3.5 sm:grid-cols-3">
        <div className="flex flex-col gap-2">
          <Field label="Complainant name" htmlFor="c-name">
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
              onChange={(e) => setValues((v) => ({ ...v, anonymous: e.target.checked, name: "", contact: "" }))}
            />
            Anonymous complaint, no name and no contact
          </label>
        </div>
        <Field label="Mobile number or email" htmlFor="c-contact">
          <input
            id="c-contact"
            className={inputClass}
            value={values.contact}
            disabled={values.anonymous}
            onChange={(e) => set("contact", e.target.value)}
          />
          <p className={muted}>Optional. Messages are sent only when a contact is recorded.</p>
        </Field>
        <Field label="Date received" htmlFor="c-date">
          <input
            id="c-date"
            type="date"
            className={inputClass}
            value={values.date}
            onChange={(e) => set("date", e.target.value)}
          />
        </Field>
      </div>
      <Field label="Medium">
        <ChoiceGroup
          label="Medium"
          choices={options.mediums.map((m) => ({ value: m.name }))}
          defaultValue={medium}
          onChange={([name]) => set("mediumId", options.mediums.find((m) => m.name === name)?.id ?? null)}
        />
      </Field>

      <Step>2 · Which transport and who</Step>
      <div className="grid gap-3.5 sm:grid-cols-3">
        <Field label="Transport">
          <ChoiceGroup
            key={vehicle?.type ?? "unknown"}
            label="Transport"
            choices={TRANSPORT}
            defaultValue={vehicle?.type === "trishaw" ? "Trishaw" : "Bus"}
          />
        </Field>
        <Field label="Vehicle number (required)" htmlFor="c-vehicle">
          <div className="relative">
            <input
              id="c-vehicle"
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
        <Field label="Complaint is about" htmlFor="c-about">
          <select
            id="c-about"
            className={inputClass}
            value={about.label}
            onChange={(e) => {
              setAbout(ABOUT.find((a) => a.label === e.target.value) ?? ABOUT[0]);
              setValues((v) => ({ ...v, personId: null, personName: "" }));
            }}
          >
            {ABOUT.map((a) => (
              <option key={a.type}>{a.label}</option>
            ))}
          </select>
        </Field>
      </div>
      <div className="grid gap-3.5 sm:grid-cols-3">
        <PersonPicker
          id="c-who"
          label="Name, if given"
          name={values.personName}
          personId={values.personId}
          personType={about.type}
          placeholder="Not known"
          onChange={(person) => setValues((v) => ({ ...v, personId: person.id, personName: person.name }))}
        />
        <Field label="Route or stand" htmlFor="c-route">
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
      </div>
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
          administrator.
        </Note>
      )}

      <Step>3 · What happened</Step>
      <div className="grid gap-3.5 sm:grid-cols-3">
        <Field label="Subject" htmlFor="c-subject">
          <input
            id="c-subject"
            className={inputClass}
            value={values.subject}
            onChange={(e) => set("subject", e.target.value)}
            onBlur={() => findDuplicates()}
          />
        </Field>
        <Field label="Category" htmlFor="c-category">
          <select
            id="c-category"
            className={inputClass}
            value={values.categoryId ?? ""}
            onChange={(e) => set("categoryId", e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Choose a category</option>
            {options.categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Evidence">
          <input
            ref={filePicker}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.webp,.txt,.eml"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) void attach(file);
            }}
          />
          <PillButton
            className="!h-11 justify-start !border-dashed"
            disabled={busy}
            onClick={() => filePicker.current?.click()}
          >
            <Icon name="attach" />
            Attach message or scan
          </PillButton>
        </Field>
      </div>
      <Field label="Description" htmlFor="c-description">
        <textarea
          id="c-description"
          className={textareaClass}
          value={values.description}
          onChange={(e) => set("description", e.target.value)}
        />
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
      </Field>
      <Field label="Severity">
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

      <DuplicatePanel candidates={candidates} onChoose={chooseDuplicate} />

      <p className={muted}>
        {status} · {done} of {REQUIRED_FIELDS} required fields done
      </p>
      <div className="flex flex-wrap items-center gap-2.5">
        <PillButton disabled={busy} onClick={saveDraft}>
          {saved?.reference ? "Save changes" : "Save draft"}
        </PillButton>
        <PillButton className="!border-amber-200 !text-amber-900" disabled={busy} onClick={markIncomplete}>
          Keep as incomplete
        </PillButton>
        <span className={muted}>A draft has no reference number yet. Incomplete issues one and pauses the clock.</span>
      </div>

      <RejectPanel suggestedEarlier={markedDuplicate} busy={busy} onReject={reject} />

      <div className="flex flex-wrap items-center justify-between gap-3.5 border-t border-[#f1ebed] pt-3.5">
        <p className={`${muted} max-w-[26rem]`}>
          A reference number is issued when you forward. A registration message goes to the complainant if a contact is
          on record, once messaging is set up.
        </p>
        <PillButton primary className="!h-11 !px-6" disabled={busy} onClick={forward}>
          Forward to {vehicle ? `${vehicle.area} ` : ""}area officer
          <Icon name="send" />
        </PillButton>
      </div>
    </div>
  );
}
