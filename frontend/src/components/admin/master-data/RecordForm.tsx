"use client";

import { useState, type FormEvent } from "react";
import { notify } from "@/lib/notify";
import { Card, eyebrow, muted } from "@/components/dashboard/ui";
import { CharCount, Field, iconButton, inputClass, textareaClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { saveRecord, type Values } from "./api";
import { ENTITIES, recordName, type EntityKey, type FieldDef, type Row } from "./entities";
import { RecordPicker } from "./RecordPicker";

function startingValues(fields: FieldDef[], row: Row | null): Values {
  const values: Values = {};
  for (const field of fields) {
    const current = row?.[field.key] as string | number | null | undefined;
    // A new record starts on the first choice of each list, for example Route or Driver.
    values[field.key] = current ?? (field.type === "select" ? field.options[0].value : field.type === "record" ? null : "");
  }
  return values;
}

// The panel beside the table: edits one record, or adds a new one when `row` is null (UI-AD-05).
export function RecordForm({
  entityKey,
  row,
  onClose,
  onSaved,
}: {
  entityKey: EntityKey;
  row: Row | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const entity = ENTITIES[entityKey];
  const [values, setValues] = useState(() => startingValues(entity.fields, row));
  // The names of the chosen records, for example the owner's name beside owner_person_id.
  const [names, setNames] = useState<Record<string, string | null>>(() =>
    Object.fromEntries(
      entity.fields.flatMap((f) => (f.type === "record" ? [[f.key, (row?.[f.shownAs] as string | null) ?? null]] : [])),
    ),
  );
  const [active, setActive] = useState(row?.is_active ?? true);
  const [busy, setBusy] = useState(false);

  const set = (key: string, value: string | number | null) => setValues((v) => ({ ...v, [key]: value }));
  const title = row ? recordName(entityKey, row) : `Add a ${entity.singular}`;

  async function submit(event: FormEvent) {
    event.preventDefault();
    const missing = entity.fields.find((f) => f.required && (values[f.key] === null || values[f.key] === ""));
    if (missing) return notify.error("Check the form", `${missing.label} is required.`);

    setBusy(true);
    const result = await saveRecord(entityKey, row?.id ?? null, values, active);
    setBusy(false);
    if (!result.ok) return notify.error(row ? "Could not save changes" : `Could not add the ${entity.singular}`, result.message);

    const name = recordName(entityKey, result.data);
    notify.success(row ? "Changes saved" : "Added", row ? `${name} was updated.` : `${name} was added.`);
    onSaved();
  }

  return (
    <Card className="animate-reveal shadow-[0_1px_2px_rgba(60,20,30,0.05),0_30px_60px_-30px_rgba(110,8,30,0.42)]">
      <form onSubmit={submit} noValidate className="flex flex-col gap-[0.9rem]">
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className={eyebrow}>{row ? "Editing" : `New ${entity.singular}`}</p>
            <h2 className="truncate text-[1.06rem] font-extrabold tracking-[-0.015em]">{title}</h2>
          </div>
          <button type="button" onClick={onClose} className={iconButton} aria-label="Close">
            <Icon name="close" size={14} />
          </button>
        </div>

        {entity.fields.map((field) => {
          const id = `record-${field.key}`;
          const value = values[field.key];
          return (
            <Field key={field.key} label={field.required ? field.label : `${field.label} (optional)`} htmlFor={id}>
              {field.type === "text" && (
                <input
                  id={id}
                  className={inputClass}
                  value={value ?? ""}
                  maxLength={field.max}
                  placeholder={field.hint}
                  onChange={(e) => set(field.key, e.target.value)}
                />
              )}
              {field.type === "textarea" && (
                <>
                  <textarea
                    id={id}
                    className={textareaClass}
                    value={value ?? ""}
                    maxLength={field.max}
                    onChange={(e) => set(field.key, e.target.value)}
                  />
                  <CharCount value={String(value ?? "")} max={field.max} />
                </>
              )}
              {field.type === "select" && (
                <select id={id} className={inputClass} value={value ?? ""} onChange={(e) => set(field.key, e.target.value)}>
                  {field.options.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              )}
              {field.type === "record" && (
                <RecordPicker
                  id={id}
                  field={field}
                  value={value as number | null}
                  label={names[field.key]}
                  onChange={(chosen, name) => {
                    set(field.key, chosen);
                    setNames((n) => ({ ...n, [field.key]: name }));
                  }}
                />
              )}
            </Field>
          );
        })}

        {row && entity.canDeactivate(row) && (
          <div className="flex items-center justify-between gap-3 rounded-2xl bg-[#f7f4f5] px-3.5 py-3">
            <div>
              <p id="record-active-label" className="text-[0.81rem] font-bold">
                Active
              </p>
              <p className={muted}>Inactive records are hidden from Level 1.</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={active}
              aria-labelledby="record-active-label"
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
          </div>
        )}

        <button
          type="submit"
          disabled={busy}
          className="focus-ring h-[2.6rem] cursor-pointer rounded-full border-[1.5px] border-crimson bg-crimson text-[0.78rem] font-bold text-white transition-colors hover:bg-crimson-hover disabled:cursor-wait disabled:opacity-60"
        >
          {busy ? "Saving…" : row ? "Save changes" : `Add ${entity.singular}`}
        </button>
        <p className={muted}>Every change is recorded in the audit trail.</p>
      </form>
    </Card>
  );
}
