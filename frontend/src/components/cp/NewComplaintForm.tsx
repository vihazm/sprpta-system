"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { inputClass, textareaClass, CharCount } from "@/components/dashboard/controls";
import { Card, eyebrow, muted } from "@/components/dashboard/ui";
import { FieldError } from "@/components/login/FieldError";
import { notify } from "@/lib/notify";
import { searchVehicles, submitComplaint, uploadFile } from "./api";
import { Combobox, type Choice } from "./Combobox";
import { EvidencePicker, releasePreviews, type PickedFile } from "./EvidencePicker";
import { withKnownType } from "./files";
import type { PortalComplaint, PortalOptions, PortalVehicle } from "./types";

const SUBJECT_MAX = 200;
const DESCRIPTION_MAX = 5000;
const SUGGESTIONS = 8;

// The browser's own calendar day, as the date box wants it (yyyy-mm-dd).
const today = () => new Date().toLocaleDateString("en-CA");

/** Routes whose name starts with what was typed first, then those with a word that starts with it. */
function matchRoutes(routes: PortalOptions["routesStands"], typed: string) {
  const t = typed.trim().toLowerCase();
  if (!t) return [];
  const starts = routes.filter((r) => r.name.toLowerCase().startsWith(t));
  const words = routes.filter(
    (r) => !r.name.toLowerCase().startsWith(t) && r.name.toLowerCase().split(/[\s\-–/]+/).some((w) => w.startsWith(t)),
  );
  return [...starts, ...words].slice(0, SUGGESTIONS);
}

type Result = { complaint: PortalComplaint; uploaded: number; failed: string[] };

/** New complaint (UI-CP-04): the standard form. Severity and vehicle checking are left to Level 1. */
export function NewComplaintForm({ options }: { options: PortalOptions }) {
  const [date, setDate] = useState(today);
  const [targetId, setTargetId] = useState("");
  const [vehicle, setVehicle] = useState("");
  const [found, setFound] = useState<PortalVehicle[]>([]);
  const [areaId, setAreaId] = useState("");
  const [routeText, setRouteText] = useState("");
  const [routeId, setRouteId] = useState<number | null>(null);
  const [categoryId, setCategoryId] = useState("");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<PickedFile[]>([]);
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [result, setResult] = useState<Result | null>(null);

  // The temporary previews of chosen photos are freed when the form goes away.
  const live = useRef(files);
  useEffect(() => {
    live.current = files;
  }, [files]);
  useEffect(() => () => releasePreviews(live.current), []);

  // While a vehicle number is typed, ask the server which numbers start that way (after a short pause).
  const query = vehicle.trim();
  useEffect(() => {
    if (!query) return;
    let stale = false;
    const timer = setTimeout(async () => {
      const reply = await searchVehicles(query);
      if (!stale && reply.ok) setFound(reply.data);
    }, 180);
    return () => {
      stale = true;
      clearTimeout(timer);
    };
  }, [query]);

  const categories = options.categories.filter(
    (c) => c.targetIds.length === 0 || (targetId !== "" && c.targetIds.includes(Number(targetId))),
  );
  const routesHere = options.routesStands.filter((p) => areaId === "" || p.areaId === null || p.areaId === Number(areaId));

  const vehicleChoices: Choice[] = (query ? found : []).slice(0, SUGGESTIONS).map((v) => ({
    key: v.vehicleNumber,
    label: v.vehicleNumber,
    hint: `${v.vehicleType === "bus" ? "Bus" : "Trishaw"} · ${v.areaName}`,
  }));
  const routeChoices: Choice[] = matchRoutes(routesHere, routeText).map((r) => ({
    key: String(r.id),
    label: r.name,
    hint: options.areas.find((a) => a.id === r.areaId)?.name,
  }));

  const errors = {
    date: !date ? "Choose the date." : date > today() ? "The date cannot be in the future." : "",
    target: targetId ? "" : "Choose who the complaint is about.",
    area: areaId ? "" : "Choose the area.",
    category: categoryId ? "" : "Choose a category.",
    subject: subject.trim() ? "" : "Add a short subject.",
    description: description.trim() ? "" : "Tell us what happened.",
  };
  const shown = (message: string) => (tried ? message : "");

  function changeTarget(next: string) {
    setTargetId(next);
    const allowed = options.categories.filter((c) => c.targetIds.length === 0 || c.targetIds.includes(Number(next)));
    if (!allowed.some((c) => String(c.id) === categoryId)) setCategoryId("");
  }

  function changeArea(next: string) {
    setAreaId(next);
    const place = options.routesStands.find((p) => p.id === routeId);
    if (place && place.areaId !== null && String(place.areaId) !== next) {
      setRouteId(null);
      setRouteText("");
    }
  }

  function pickVehicle(choice: Choice) {
    setVehicle(choice.label);
    const match = found.find((v) => v.vehicleNumber === choice.label);
    if (match && !areaId) changeArea(String(match.areaId)); // the vehicle's own area, unless one was already chosen
  }

  function pickRoute(choice: Choice) {
    const place = options.routesStands.find((p) => String(p.id) === choice.key);
    if (!place) return;
    setRouteText(place.name);
    setRouteId(place.id);
    if (!areaId && place.areaId !== null) setAreaId(String(place.areaId));
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setTried(true);
    if (Object.values(errors).some(Boolean)) return;

    setBusy(true);
    const created = await submitComplaint({
      complaintDate: date,
      targetTypeId: Number(targetId),
      subject,
      vehicleNumber: vehicle,
      areaId: Number(areaId),
      routeStandId: routeId,
      categoryId: Number(categoryId),
      description,
    });
    if (!created.ok) {
      setBusy(false);
      return notify.error("Complaint not submitted", created.message);
    }

    // The complaint exists now. A file that fails does not undo it; the person is told which ones to add again.
    let uploaded = 0;
    const failed: string[] = [];
    for (const [i, picked] of files.entries()) {
      setProgress(`Uploading file ${i + 1} of ${files.length}…`);
      const sent = await uploadFile(created.data.id, withKnownType(picked.file));
      if (sent.ok) uploaded += 1;
      else failed.push(`${picked.file.name}: ${sent.message}`);
    }
    releasePreviews(files);
    setBusy(false);
    setProgress("");
    notify.success("Complaint submitted", "SPRPTA will check it first.");
    setResult({ complaint: created.data, uploaded, failed });
  }

  if (result) return <Submitted result={result} />;

  return (
    <form noValidate onSubmit={onSubmit} className="flex flex-col gap-5">
      <div>
        <p className={eyebrow}>New complaint</p>
        <h1 className="mt-1.5 font-display text-[2.3rem] leading-[1.08] tracking-[-0.035em] max-[599px]:text-[1.8rem]">
          Describe what happened
        </h1>
        <p className={`mt-2 ${muted}`}>SPRPTA staff check every complaint before it is processed.</p>
      </div>

      <Section n={1} title="Who and when">
        <Field label="Date of the incident" id="cp-date" error={shown(errors.date)}>
          <input
            id="cp-date"
            type="date"
            className={inputClass}
            value={date}
            max={today()}
            onChange={(e) => setDate(e.target.value)}
            aria-invalid={!!shown(errors.date)}
            aria-describedby="cp-date-err"
          />
        </Field>
        <Field label="Complaint is about" id="cp-target" error={shown(errors.target)}>
          <select
            id="cp-target"
            className={inputClass}
            value={targetId}
            onChange={(e) => changeTarget(e.target.value)}
            aria-invalid={!!shown(errors.target)}
            aria-describedby="cp-target-err"
          >
            <option value="">Choose…</option>
            {options.targets.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Vehicle number (if you know it)" id="cp-vehicle" optional>
          <Combobox
            id="cp-vehicle"
            value={vehicle}
            onType={(text) => setVehicle(text.toUpperCase())}
            choices={vehicleChoices}
            onPick={pickVehicle}
            placeholder="Start typing, e.g. SP NB"
            maxLength={20}
          />
        </Field>
      </Section>

      <Section n={2} title="Where">
        <Field label="Area" id="cp-area" error={shown(errors.area)}>
          <select
            id="cp-area"
            className={inputClass}
            value={areaId}
            onChange={(e) => changeArea(e.target.value)}
            aria-invalid={!!shown(errors.area)}
            aria-describedby="cp-area-err"
          >
            <option value="">Choose…</option>
            {options.areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Route or stand (optional)" id="cp-route" optional>
          <Combobox
            id="cp-route"
            value={routeText}
            onType={(text) => {
              setRouteText(text);
              if (routeId !== null) setRouteId(null); // typing again means it is no longer the one that was picked
            }}
            choices={routeChoices}
            onPick={pickRoute}
            placeholder="Start typing a route or stand"
            emptyNote="No route or stand starts like that. You can leave this empty."
            onBlurText={() => {
              if (routeId === null) setRouteText(""); // only a route picked from the list is kept
            }}
          />
        </Field>
      </Section>

      <Section n={3} title="What happened" stacked>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(14rem,1fr))] gap-4">
          <Field label="Subject" id="cp-subject" error={shown(errors.subject)}>
            <input
              id="cp-subject"
              className={inputClass}
              placeholder="A short title for the problem"
              maxLength={SUBJECT_MAX}
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              aria-invalid={!!shown(errors.subject)}
              aria-describedby="cp-subject-err"
            />
          </Field>
          <Field label="Category" id="cp-category" error={shown(errors.category)}>
            <select
              id="cp-category"
              className={inputClass}
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              aria-invalid={!!shown(errors.category)}
              aria-describedby="cp-category-err"
            >
              <option value="">{targetId ? "Choose…" : "Choose who it is about first"}</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="Description" id="cp-description" error={shown(errors.description)}>
          <textarea
            id="cp-description"
            className={`${textareaClass} !h-[8rem]`}
            placeholder="Describe what happened, where and when"
            maxLength={DESCRIPTION_MAX}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            aria-invalid={!!shown(errors.description)}
            aria-describedby="cp-description-err"
          />
          <CharCount value={description} max={DESCRIPTION_MAX} />
        </Field>
      </Section>

      <Section n={4} title="Evidence (optional)" stacked>
        <EvidencePicker picked={files} onChange={setFiles} disabled={busy} />
      </Section>

      <div className="sticky bottom-3 z-10 flex flex-wrap items-center justify-between gap-3 rounded-[1.4rem] bg-white/95 px-5 py-3.5 shadow-[0_18px_40px_-16px_rgba(60,20,30,0.35),0_0_0_1px_rgba(60,20,30,0.06)] backdrop-blur-md">
        <p className={`max-w-[26rem] ${muted}`}>
          Your name and contact come from your account. Severity and vehicle details are confirmed by SPRPTA staff.
        </p>
        <div className="flex gap-2.5">
          <Link
            href="/cp/dashboard"
            className="focus-ring inline-flex h-12 items-center rounded-[0.95rem] bg-white px-6 text-[0.9rem] font-bold text-slate-ink shadow-[0_0_0_1px_rgba(60,20,30,0.08)] transition-colors hover:bg-field"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={busy}
            className="focus-ring h-12 cursor-pointer rounded-[0.95rem] bg-crimson px-6 text-[0.9rem] font-extrabold text-white transition-colors hover:bg-crimson-hover disabled:cursor-wait disabled:opacity-70"
          >
            {busy ? progress || "Submitting…" : "Submit complaint"}
          </button>
        </div>
      </div>
    </form>
  );
}

function Section({ n, title, stacked = false, children }: { n: number; title: string; stacked?: boolean; children: ReactNode }) {
  return (
    <Card className="!flex-row !gap-[1.1rem] !p-[1.6rem] max-[599px]:!flex-col max-[599px]:!gap-3">
      <span className="grid size-[1.9rem] flex-none place-items-center rounded-[0.65rem] bg-crimson text-[0.8rem] font-extrabold text-white">
        {n}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <h2 className="font-display text-[1.25rem] leading-[1.2]">{title}</h2>
        {stacked ? (
          <div className="flex flex-col gap-4">{children}</div>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fit,minmax(14rem,1fr))] gap-4">{children}</div>
        )}
      </div>
    </Card>
  );
}

function Field({
  label,
  id,
  error = "",
  optional = false,
  children,
}: {
  label: string;
  id: string;
  error?: string;
  optional?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-[0.4rem]">
      <label htmlFor={id} className="text-[0.78rem] font-bold text-ink">
        {label}
        {!optional && <span className="text-crimson"> *</span>}
      </label>
      {children}
      <FieldError id={`${id}-err`} message={error} />
    </div>
  );
}

/** What the person sees right after submitting. There is no reference number yet: Level 1 issues it. */
function Submitted({ result }: { result: Result }) {
  const { complaint, uploaded, failed } = result;
  return (
    <Card className="max-w-[40rem] items-start gap-4 !p-9">
      <span className="grid size-16 place-items-center rounded-full bg-emerald-50 text-[1.8rem] font-extrabold text-emerald-800" aria-hidden="true">
        ✓
      </span>
      <h1 className="font-display text-[2rem] leading-[1.1]">Complaint submitted</h1>
      <p className="max-w-[30rem] text-[0.92rem] leading-[1.55] text-muted">
        Thank you. SPRPTA staff will check it first. You will be told by SMS or email once it is registered and given a
        reference number.
      </p>
      {uploaded > 0 && (
        <p className="text-[0.85rem] font-bold text-emerald-800">
          {uploaded} {uploaded === 1 ? "file" : "files"} attached.
        </p>
      )}
      {failed.length > 0 && (
        <div role="alert" className="rounded-[1rem] bg-[#fff6f5] px-4 py-3">
          <p className="m-0 text-[0.85rem] font-extrabold text-error">
            {failed.length} {failed.length === 1 ? "file was" : "files were"} not attached
          </p>
          <ul className="m-0 mt-1 list-none p-0 text-[0.8rem] text-error">
            {failed.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
          <p className={`m-0 mt-2 ${muted}`}>The complaint itself is saved. You can add the files again from My complaints.</p>
        </div>
      )}
      <div className="mt-1 flex flex-wrap gap-2.5">
        <Link
          href={`/cp/complaints?id=${complaint.id}`}
          className="focus-ring inline-flex h-12 items-center rounded-[0.95rem] bg-crimson px-6 text-[0.9rem] font-extrabold text-white transition-colors hover:bg-crimson-hover"
        >
          View my complaints
        </Link>
        <Link
          href="/cp/dashboard"
          className="focus-ring inline-flex h-12 items-center rounded-[0.95rem] bg-field px-6 text-[0.9rem] font-bold text-slate-ink transition-colors hover:bg-[#e7e8eb]"
        >
          Back to dashboard
        </Link>
      </div>
    </Card>
  );
}
