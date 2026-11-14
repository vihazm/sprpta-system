"use client";

import { useEffect, useState } from "react";
import { ChoiceGroup } from "@/components/dashboard/ChoiceGroup";
import { Field, inputClass, textareaClass } from "@/components/dashboard/controls";
import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, PillButton } from "@/components/dashboard/ui";
import { notify } from "@/lib/notify";
import { loadOptions, saveRecommendation } from "@/components/l1/entry/api";
import { PersonPicker } from "@/components/l1/entry/PersonPicker";
import type { Option, RecommendationFields } from "@/components/l1/entry/types";

const KINDS = [{ value: "Improvement suggestion" }, { value: "Commendation" }];

function today() {
  return new Date().toLocaleDateString("en-CA"); // yyyy-mm-dd in the browser's own time zone
}

const blank: RecommendationFields = { kind: "commendation", details: "", mediumId: null, date: "", personId: null };

// A suggestion to improve the service, or praise for a person (UC-L1-11). Used by the dashboard
// and by the full New recommendation page. L1 cannot open a recommendation again after saving it.
export function RecommendationForm({ className = "" }: { className?: string }) {
  const [values, setValues] = useState<RecommendationFields>(blank);
  const [personName, setPersonName] = useState("");
  const [mediums, setMediums] = useState<Option[]>([]);
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [formKey, setFormKey] = useState(0); // remounts the choice buttons after a save

  useEffect(() => {
    let current = true;
    (async () => {
      const lists = await loadOptions();
      if (!current) return;
      if (lists.ok) setMediums(lists.data.mediums);
      setValues((v) => ({ ...v, date: v.date || today() }));
    })();
    return () => {
      current = false;
    };
  }, []);

  function set<K extends keyof RecommendationFields>(key: K, value: RecommendationFields[K]) {
    setConfirmed(false);
    setValues((v) => ({ ...v, [key]: value }));
  }

  async function save() {
    if (!values.details.trim()) return notify.error("Check the form", "Write the details of the recommendation.");
    if (values.kind === "commendation" && values.personId === null) {
      return notify.error("Check the form", "Pick the person who is being commended from the records.");
    }
    setBusy(true);
    const result = await saveRecommendation(values);
    setBusy(false);
    if (!result.ok) return notify.error("Could not save the recommendation", result.message);

    notify.success("Recommendation saved", "It is now with Level 2 and Level 3.");
    setValues({ ...blank, kind: values.kind, date: today() });
    setPersonName("");
    setFormKey((key) => key + 1);
    setConfirmed(true);
  }

  const commendation = values.kind === "commendation";

  return (
    <Card className={className}>
      <CardHeading
        title="Log a recommendation"
        subtitle="A suggestion to improve the service, or praise for a person"
      />
      <ChoiceGroup
        key={formKey}
        label="Kind of recommendation"
        choices={KINDS}
        defaultValue={commendation ? "Commendation" : "Improvement suggestion"}
        onChange={([kind]) => set("kind", kind === "Commendation" ? "commendation" : "improvement")}
      />
      {commendation && (
        <PersonPicker
          id="rec-person"
          label="Person commended"
          name={personName}
          personId={values.personId}
          placeholder="Search by name"
          hint="Pick the person from the records."
          onChange={(person) => {
            setPersonName(person.name);
            set("personId", person.id);
          }}
        />
      )}
      <div className="grid gap-3.5 sm:grid-cols-2">
        <Field label="Medium" htmlFor="rec-medium">
          <select
            id="rec-medium"
            className={inputClass}
            value={values.mediumId ?? ""}
            onChange={(e) => set("mediumId", e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Not recorded</option>
            {mediums.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Date received" htmlFor="rec-date">
          <input
            id="rec-date"
            type="date"
            className={inputClass}
            value={values.date}
            onChange={(e) => set("date", e.target.value)}
          />
        </Field>
      </div>
      <Field label="Details" htmlFor="rec-details">
        <textarea
          id="rec-details"
          className={textareaClass}
          value={values.details}
          onChange={(e) => set("details", e.target.value)}
        />
      </Field>
      <PillButton primary className="self-start" disabled={busy} onClick={save}>
        Save recommendation
      </PillButton>
      {confirmed && (
        <Note tone="good">Saved. It is now with Level 2 and Level 3, and it will not appear here again.</Note>
      )}
      <Note className="mt-auto">
        After you save, only Level 2 and Level 3 can see it. It will not appear here again.
      </Note>
    </Card>
  );
}
