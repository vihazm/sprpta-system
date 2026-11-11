import { ChoiceGroup } from "@/components/dashboard/ChoiceGroup";
import { Field, inputClass, textareaClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { SEVERITY_CHOICES, SEVERITY_LABEL } from "@/components/dashboard/severity";
import { Card, Chip, LinkButton, PillButton, muted } from "@/components/dashboard/ui";
import type { ComplaintDraft } from "./types";

const MEDIUMS = ["WhatsApp", "Email", "SMS", "Letter", "Phone call", "Walk-in"].map((value) => ({ value }));
const TRANSPORT = ["Bus", "Trishaw"].map((value) => ({ value }));
const REJECT_REASONS = ["Invalid", "Spam", "Out of jurisdiction", "Duplicate of an earlier case"].map((value) => ({
  value,
}));

// Fields filled in from the vehicle record are shown in green.
const filledIn = `${inputClass} !bg-emerald-50`;

function Step({ children }: { children: string }) {
  return <p className="text-[0.69rem] font-extrabold uppercase tracking-[0.09em] text-crimson">{children}</p>;
}

// Entering a complaint that arrived by any medium (UC-L1-01 to UC-L1-10), all in one place.
export function QuickEntry({ draft, className = "" }: { draft: ComplaintDraft; className?: string }) {
  const duplicateChoices = [
    { value: "Not a duplicate" },
    { value: `Duplicate of ${draft.duplicate.ref}` },
    { value: "Related, link them" },
  ];

  return (
    <Card className={`gap-4 ${className}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-[1.25rem] font-extrabold tracking-[-0.015em]">Quick entry</h3>
          <p className={`mt-0.5 ${muted}`}>
            Every detail of a complaint in one place. Details filled in from the records are shown in green.
          </p>
        </div>
        <Chip tone="ok">Saved automatically</Chip>
      </div>

      <div className="flex flex-col gap-4">
        <Step>1 · Who sent it and how</Step>
        <div className="grid gap-3.5 sm:grid-cols-3">
          <div className="flex flex-col gap-2">
            <Field label="Complainant name" htmlFor="c-name">
              <input id="c-name" className={inputClass} defaultValue={draft.name} />
            </Field>
            <label className="flex items-center gap-2 text-[0.75rem] text-slate-600">
              <input type="checkbox" className="accent-crimson" />
              Anonymous complaint, no name and no contact
            </label>
          </div>
          <Field label="Mobile number or email" htmlFor="c-contact">
            <input id="c-contact" className={inputClass} defaultValue={draft.contact} />
            <p className={muted}>Optional. Messages are sent only when a contact is recorded.</p>
          </Field>
          <Field label="Date received" htmlFor="c-date">
            <input id="c-date" className={inputClass} defaultValue={draft.received} />
          </Field>
        </div>
        <Field label="Medium">
          <ChoiceGroup label="Medium" choices={MEDIUMS} defaultValue={draft.medium} />
        </Field>

        <Step>2 · Which transport and who</Step>
        <div className="grid gap-3.5 sm:grid-cols-3">
          <Field label="Transport">
            <ChoiceGroup label="Transport" choices={TRANSPORT} defaultValue={draft.transport} />
          </Field>
          <Field label="Vehicle number (required)" htmlFor="c-vehicle">
            <div className="relative">
              <input id="c-vehicle" className={`${inputClass} pr-[5rem]`} defaultValue={draft.vehicle} />
              <span className="absolute right-2 top-[0.55rem]">
                <Chip tone="ok">Found</Chip>
              </span>
            </div>
          </Field>
          <Field label="Complaint is about" htmlFor="c-about">
            <select id="c-about" className={inputClass} defaultValue={draft.about}>
              <option>Driver</option>
              <option>Conductor</option>
              <option>SPRPTA staff</option>
            </select>
          </Field>
        </div>
        <div className="grid gap-3.5 sm:grid-cols-3">
          <Field label="Name, if given" htmlFor="c-who">
            <input id="c-who" className={inputClass} placeholder="Not known" />
          </Field>
          <Field label="Route or stand" htmlFor="c-route">
            <input id="c-route" className={filledIn} defaultValue={draft.route} />
          </Field>
          <Field label="Area" htmlFor="c-area">
            <input id="c-area" className={filledIn} defaultValue={`${draft.area} (from the vehicle)`} />
          </Field>
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 rounded-[1.1rem] bg-emerald-50 px-4 py-3 text-[0.78rem] text-emerald-900">
          <b className="inline-flex items-center gap-1.5 font-extrabold">
            <Icon name="check" size={14} />
            Vehicle found, permit valid
          </b>
          <span>
            Permit <b>{draft.lookup.permit}</b>
          </span>
          <span>
            Owner <b>{draft.lookup.owner}</b>
          </span>
          <span>
            Registered area <b>{draft.area}</b>
          </span>
          <span>
            Past complaints <b>{draft.lookup.pastComplaints}</b>
          </span>
        </div>

        <Step>3 · What happened</Step>
        <div className="grid gap-3.5 sm:grid-cols-3">
          <Field label="Subject" htmlFor="c-subject">
            <input id="c-subject" className={inputClass} defaultValue={draft.subject} />
          </Field>
          <Field label="Category" htmlFor="c-category">
            <select id="c-category" className={inputClass} defaultValue={draft.category}>
              <option>Staff behaviour</option>
              <option>Overcharging</option>
              <option>Reckless driving</option>
              <option>Timetable or route</option>
            </select>
          </Field>
          <Field label="Evidence">
            <PillButton className="!h-11 justify-start !border-dashed">
              <Icon name="attach" />
              Attach message or scan
            </PillButton>
          </Field>
        </div>
        <Field label="Description" htmlFor="c-description">
          <textarea id="c-description" className={textareaClass} defaultValue={draft.description} />
          <div className="flex flex-wrap gap-2">
            {draft.attachments.map((file) => (
              <Chip key={file}>{file}</Chip>
            ))}
          </div>
        </Field>
        <Field label="Severity">
          <ChoiceGroup
            label="Severity"
            choices={SEVERITY_CHOICES}
            defaultValue={SEVERITY_LABEL[draft.severity]}
            look="dark"
          />
          <p className={muted}>
            Forward by: Critical the same day · High 1 day · Medium 2 days · Low 3 days. The clock starts at
            registration.
          </p>
        </Field>

        <div className="flex flex-col gap-2.5 rounded-[1.25rem] bg-amber-50 px-4 py-3.5">
          <div className="flex flex-wrap items-center justify-between gap-2.5">
            <p className="text-[0.81rem] font-extrabold text-amber-900">
              1 possible duplicate: {draft.duplicate.ref}, {draft.duplicate.summary}, {draft.duplicate.match}% match
            </p>
            <LinkButton>Compare side by side</LinkButton>
          </div>
          <ChoiceGroup label="Duplicate check" choices={duplicateChoices} defaultValue="Not a duplicate" />
          <p className="text-[0.75rem] text-amber-900">
            Nothing is merged or deleted. A duplicate is rejected with a reason that names the earlier case.
          </p>
        </div>

        <p className={muted}>Saved automatically · 8 of 9 required fields done</p>
        <div className="flex flex-wrap items-center gap-2.5">
          <PillButton>Save draft</PillButton>
          <PillButton className="!border-amber-200 !text-amber-900">Keep as incomplete</PillButton>
          <span className={muted}>A draft has no reference number yet. Incomplete issues one and pauses the clock.</span>
        </div>

        <div className="flex flex-col gap-3 rounded-[1.25rem] border-[1.5px] border-dashed border-[#e8c9cf] p-4">
          <p className="text-[0.81rem] font-extrabold text-crimson-hover">Cannot be forwarded? Reject with a reason</p>
          <ChoiceGroup
            label="Reason for rejecting"
            choices={REJECT_REASONS}
            defaultValue="Duplicate of an earlier case"
          />
          <div className="grid items-end gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto]">
            <Field label="Reason (required)" htmlFor="r-why">
              <input id="r-why" className={inputClass} placeholder="For example: same incident as the earlier case" />
            </Field>
            <Field label="Earlier case" htmlFor="r-ref">
              <input id="r-ref" className={inputClass} defaultValue={draft.duplicate.ref} />
            </Field>
            <PillButton className="!h-11 !border-red-200 !text-red-800">Reject case</PillButton>
          </div>
          <p className={muted}>Rejected is final. Level 3 cannot reinstate a rejected case.</p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3.5 border-t border-[#f1ebed] pt-3.5">
          <p className={`${muted} max-w-[26rem]`}>
            A reference number is issued when you forward. A registration message goes to the complainant if a
            contact is on record.
          </p>
          <PillButton primary className="!h-11 !px-6">
            Forward to {draft.area} area officer
            <Icon name="send" />
          </PillButton>
        </div>
      </div>
    </Card>
  );
}
