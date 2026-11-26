"use client";

import { useState, type FormEvent } from "react";
import { CharCount, Field, inputClass, textareaClass } from "@/components/dashboard/controls";
import { Chip, muted } from "@/components/dashboard/ui";
import { notify } from "@/lib/notify";
import { saveTemplate, type Template } from "./api";

const MAX_BODY = 2000;
const SMS_PART = 160; // characters in one text message

// What the preview fills the placeholders with.
const SAMPLE: Record<string, string> = {
  reference_number: "SPRPTA-2026-000123",
  solution_text: "The driver is suspended for three days and must attend a road safety course.",
  code: "482913",
  minutes: "10",
};

function fill(text: string) {
  return text.replace(/\{(\w+)\}/g, (whole, name: string) => SAMPLE[name] ?? whole);
}

// A fixed locale and time zone keep the server and the browser rendering the same text.
const editedOn = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "Asia/Colombo" });

/** One channel of one message: its wording, a switch, and a preview with sample values. */
export function TemplateEditor({ initial }: { initial: Template }) {
  const [saved, setSaved] = useState(initial);
  const [subject, setSubject] = useState(initial.subject ?? "");
  const [body, setBody] = useState(initial.body);
  const [active, setActive] = useState(initial.active);
  const [busy, setBusy] = useState(false);

  const email = saved.channel === "email";
  const id = `${saved.messageType}-${saved.channel}`;
  const changed = body !== saved.body || active !== saved.active || (email && subject !== (saved.subject ?? ""));
  const preview = fill(body);
  const parts = Math.max(1, Math.ceil(preview.length / SMS_PART));

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!body.trim()) return notify.error("Check the message", "The message cannot be empty.");
    if (email && !subject.trim()) return notify.error("Check the message", "An email needs a subject.");

    setBusy(true);
    const result = await saveTemplate(saved, { subject, body, active });
    setBusy(false);
    if (!result.ok) return notify.error("Could not save the message", result.message);
    setSaved(result.data);
    setSubject(result.data.subject ?? "");
    setBody(result.data.body);
    notify.success("Message saved", `${saved.label} (${email ? "email" : "text message"}) is updated.`);
  }

  return (
    <form onSubmit={submit} noValidate className="flex min-w-0 flex-col gap-3 rounded-[1.25rem] bg-[#f7f4f5] p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-[0.9rem] font-extrabold">{email ? "Email" : "Text message (SMS)"}</h3>
        {saved.canSwitchOff ? (
          <button
            type="button"
            role="switch"
            aria-checked={active}
            aria-label={`Send this ${email ? "email" : "text message"}`}
            onClick={() => setActive(!active)}
            className={`focus-ring relative h-[1.6rem] w-11 flex-none cursor-pointer rounded-full transition-colors ${
              active ? "bg-emerald-500" : "bg-slate-300"
            }`}
          >
            <span
              className={`absolute top-[0.2rem] size-5 rounded-full bg-white transition-all ${
                active ? "left-[1.4rem]" : "left-[0.2rem]"
              }`}
            />
          </button>
        ) : (
          <Chip tone="ok">Always sent</Chip>
        )}
      </div>

      {email && (
        <Field label="Subject" htmlFor={`${id}-subject`}>
          <input
            id={`${id}-subject`}
            className={`${inputClass} !bg-white`}
            value={subject}
            maxLength={200}
            onChange={(e) => setSubject(e.target.value)}
          />
        </Field>
      )}
      <Field label="Message" htmlFor={`${id}-body`}>
        <textarea
          id={`${id}-body`}
          className={`${textareaClass} !h-[7.5rem] !bg-white`}
          value={body}
          maxLength={MAX_BODY}
          onChange={(e) => setBody(e.target.value)}
        />
        <CharCount value={body} max={MAX_BODY} />
      </Field>

      <div className="rounded-2xl bg-white px-3.5 py-3">
        <p className="text-[0.69rem] font-bold uppercase tracking-[0.09em] text-muted">Preview</p>
        {email && <p className="mt-1 text-[0.81rem] font-bold">{fill(subject)}</p>}
        <p className="mt-1 whitespace-pre-line break-words text-[0.81rem] leading-[1.5]">{preview}</p>
        {!email && (
          <p className={`mt-1.5 ${muted}`}>
            About {preview.length} characters, {parts} text message{parts === 1 ? "" : "s"}.
          </p>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className={muted}>
          {saved.edited && saved.updatedAt
            ? `Edited by ${saved.updatedBy ?? "an administrator"} on ${editedOn.format(new Date(saved.updatedAt))}`
            : "Default wording"}
          {!active && " · switched off, not sent"}
        </p>
        <button
          type="submit"
          disabled={busy || !changed}
          className="focus-ring h-[2.4rem] cursor-pointer rounded-full border-[1.5px] border-crimson bg-crimson px-5 text-[0.78rem] font-bold text-white transition-colors hover:bg-crimson-hover disabled:cursor-default disabled:opacity-50"
        >
          {busy ? "Saving…" : "Save"}
        </button>
      </div>
    </form>
  );
}
