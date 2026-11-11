import { ChoiceGroup } from "@/components/dashboard/ChoiceGroup";
import { Field, inputClass, textareaClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { PillButton, muted } from "@/components/dashboard/ui";

const ACTIONS = ["Warning", "Fine", "Suspension", "Legal action", "No action"].map((value) => ({ value }));
const OUTCOMES = ["Substantiated", "Partly substantiated", "Not substantiated"].map((value) => ({ value }));
const FOLLOWED = ["Followed", "Not followed", "Not used"].map((value) => ({ value }));

// Recording the decision, creating the solution document or escalating (UC-L2-04, 05 and 07).
export function DecisionForm() {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-[0.69rem] font-extrabold uppercase tracking-[0.09em] text-crimson">Your decision</p>
      <Field label="Action">
        <ChoiceGroup label="Action" choices={ACTIONS} defaultValue="Suspension" />
      </Field>
      <div className="grid gap-3.5 sm:grid-cols-2">
        <Field label="Outcome">
          <ChoiceGroup label="Outcome" choices={OUTCOMES} defaultValue="Substantiated" />
        </Field>
        <Field label="Was the AI suggestion followed?">
          <ChoiceGroup label="AI suggestion followed" choices={FOLLOWED} defaultValue="Followed" />
        </Field>
      </div>
      <Field label="Reason for the decision (required)" htmlFor="decision-reason">
        <textarea
          id="decision-reason"
          className={textareaClass}
          defaultValue="3-day suspension, given the earlier substantiated complaint and the safety risk."
        />
      </Field>

      <div className="flex flex-wrap items-center gap-3.5 rounded-[1.25rem] border-[1.5px] border-dashed border-[#e3c5cb] px-4 py-3.5">
        <span className="flex size-[2.3rem] flex-none items-center justify-center rounded-xl bg-field text-slate-600">
          <Icon name="file" size={18} />
        </span>
        <div className="min-w-[14rem] flex-1">
          <p className="text-[0.84rem] font-extrabold">Solution document (PDF)</p>
          <p className={muted}>
            Holds the case ID, a short summary and the verdict. The status becomes Awaiting implementation. Give the
            PDF to the implementing staff outside this system.
          </p>
        </div>
        <PillButton className="!border-crimson !text-crimson-hover">Create solution document</PillButton>
      </div>

      <p className="flex items-start gap-2.5 rounded-2xl bg-emerald-50 px-3.5 py-3 text-[0.78rem] leading-[1.45] text-emerald-900">
        <span className="mt-0.5 flex-none">
          <Icon name="message" size={16} />
        </span>
        <span>
          <b className="font-extrabold">Message to the complainant.</b> When you record the decision, the complainant
          is told which solution was given. It is sent only if a mobile number or email was recorded, and a failed
          message never blocks the case.
        </span>
      </p>

      <div className="flex flex-wrap items-end justify-between gap-4 border-t border-[#f1ebed] pt-3.5">
        <div className="flex min-w-[18rem] flex-[1_1_22rem] flex-wrap items-end gap-2.5">
          <div className="min-w-[14rem] flex-1">
            <Field label="Reason to escalate to Level 3 (required)" htmlFor="escalate-reason">
              <input
                id="escalate-reason"
                className={inputClass}
                placeholder="Only if you cannot resolve it within your area"
              />
            </Field>
          </div>
          <PillButton className="!h-11 !border-crimson !text-crimson-hover">
            <Icon name="up" size={14} />
            Escalate to Level 3
          </PillButton>
        </div>
        <PillButton primary className="!h-11 !px-6">
          <Icon name="check" size={14} />
          Record decision
        </PillButton>
      </div>
    </div>
  );
}
