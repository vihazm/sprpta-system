"use client";

import { useState, type FormEvent } from "react";
import { ROLE_LABEL } from "@/lib/roles";
import { notify } from "@/lib/notify";
import { Card, eyebrow, muted } from "../dashboard/ui";
import { createUser, unlockUser, updateUser } from "./api";
import { Field, iconButton, inputClass } from "./controls";
import { formatDay, formatWhen } from "./format";
import { Icon } from "./icons";
import { AVATAR_TINT, ROLE_ORDER, initials } from "./staff";
import type { AreaOfficer, StaffRole, StaffUser } from "./types";

// Pre-fills a new user, for example when assigning an officer to an uncovered area.
export type Preset = { role: StaffRole; areaId: number };

const PASSWORD_LETTERS = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // no look-alikes
const MIN_PASSWORD_LENGTH = 8;

function generatePassword() {
  const random = crypto.getRandomValues(new Uint8Array(12));
  return Array.from(random, (n) => PASSWORD_LETTERS[n % PASSWORD_LETTERS.length]).join("");
}

// The panel beside the directory: edits one account, or starts a new one when `user` is null.
export function EditUserPanel({
  user,
  preset,
  areas,
  onClose,
  onSaved,
}: {
  user: StaffUser | null;
  preset?: Preset;
  areas: AreaOfficer[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(user?.name ?? "");
  const [login, setLogin] = useState(user?.login ?? "");
  const [password, setPassword] = useState(() => (user ? "" : generatePassword()));
  const [role, setRole] = useState<StaffRole>(user?.role ?? preset?.role ?? "l1");
  const [areaId, setAreaId] = useState<number | null>(user?.areaId ?? preset?.areaId ?? null);
  const [active, setActive] = useState(user ? user.status !== "inactive" : true);
  const [busy, setBusy] = useState(false);

  // What is wrong with the form, if anything. The server checks again and has the final say.
  function problem() {
    if (!name.trim()) return "Enter the person's full name.";
    if (!login.trim()) return "Enter an email address or a phone number to sign in with.";
    if (!user && password.length < MIN_PASSWORD_LENGTH) {
      return `The first password needs at least ${MIN_PASSWORD_LENGTH} characters.`;
    }
    if (role === "l2" && areaId === null) return "Choose an area for a Level 2 officer.";
    return null;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const issue = problem();
    if (issue) return notify.error("Check the form", issue);

    const form = { name: name.trim(), login: login.trim(), role, areaId, active };
    setBusy(true);
    const result = user ? await updateUser(user.id, form) : await createUser(form, password);
    setBusy(false);

    if (!result.ok) {
      return notify.error(user ? "Could not save changes" : "Could not create user", result.message);
    }
    if (user) notify.success("Changes saved", `${form.name} was updated.`);
    else notify.success("User created", `${form.name} can now sign in.`);
    onSaved();
  }

  async function unlock() {
    if (!user) return;
    setBusy(true);
    const result = await unlockUser(user.id);
    setBusy(false);

    if (!result.ok) return notify.error("Could not unlock", result.message);
    notify.success("Account unlocked", `${user.name} can sign in again.`);
    onSaved();
  }

  return (
    <Card className="shadow-[0_1px_2px_rgba(60,20,30,0.05),0_30px_60px_-30px_rgba(110,8,30,0.42)]">
      <form onSubmit={submit} noValidate className="flex flex-col gap-[0.9rem]">
        <div className="flex items-center gap-3">
          <div
            className={`flex size-12 flex-none items-center justify-center rounded-full text-[0.9rem] font-extrabold ${AVATAR_TINT[role]}`}
          >
            {name.trim() ? initials(name.trim()) : "+"}
          </div>
          <div className="min-w-0 flex-1">
            <p className={eyebrow}>{user ? "Editing" : "New user"}</p>
            <h2 className="truncate text-[1.06rem] font-extrabold tracking-[-0.015em]">
              {user ? user.name : "Create a user"}
            </h2>
          </div>
          <button type="button" onClick={onClose} className={iconButton} aria-label="Close">
            <Icon name="close" size={14} />
          </button>
        </div>

        <Field label="Full name" htmlFor="user-name">
          <input id="user-name" className={inputClass} value={name} onChange={(e) => setName(e.target.value)} />
        </Field>

        <Field label="Login (email or phone number)" htmlFor="user-login">
          <input id="user-login" className={inputClass} value={login} onChange={(e) => setLogin(e.target.value)} />
        </Field>

        {!user && (
          <Field label="First password" htmlFor="user-password">
            <div className="flex gap-2">
              <input
                id="user-password"
                className={`${inputClass} min-w-0 flex-1`}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="off"
              />
              <button
                type="button"
                onClick={() => setPassword(generatePassword())}
                className="focus-ring h-11 cursor-pointer rounded-full border-[1.5px] border-[#E5E7EB] bg-white px-4 text-[0.78rem] font-bold text-slate-ink transition-colors hover:border-crimson hover:text-crimson"
              >
                Generate
              </button>
            </div>
            <p className={muted}>Give it to them securely. It is not shown again.</p>
          </Field>
        )}

        <Field label="Role" htmlFor="user-role">
          <select
            id="user-role"
            className={inputClass}
            value={role}
            onChange={(e) => setRole(e.target.value as StaffRole)}
          >
            {ROLE_ORDER.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABEL[r]}
              </option>
            ))}
          </select>
        </Field>

        {role === "l2" && (
          <Field label="Area">
            <div className="flex flex-col gap-2">
              {areas.map((area) => {
                const taken = area.officerId !== null && area.officerId !== user?.id;
                const chosen = areaId === area.id;
                return (
                  <button
                    key={area.id}
                    type="button"
                    disabled={taken}
                    onClick={() => setAreaId(area.id)}
                    aria-pressed={chosen}
                    className={`focus-ring flex min-w-0 cursor-pointer items-center justify-between gap-2 rounded-2xl border-[1.5px] px-3.5 py-2.5 text-left text-[0.81rem] font-bold disabled:cursor-not-allowed disabled:border-dashed disabled:bg-[#f7f4f5] disabled:text-[#9AA0AA] ${
                      chosen ? "border-crimson bg-crimson/10 text-crimson-deep" : "border-[#E5E7EB] bg-white"
                    }`}
                  >
                    {area.name}
                    <small className="truncate text-[0.72rem] font-medium text-muted">
                      {taken ? area.officerName : chosen ? "This person" : "Free"}
                    </small>
                  </button>
                );
              })}
            </div>
          </Field>
        )}

        {user && (
          <div className="flex items-center justify-between gap-3 rounded-2xl bg-[#f7f4f5] px-3.5 py-3">
            <div>
              <p id="active-label" className="text-[0.81rem] font-bold">
                Account is active
              </p>
              <p className={muted}>Last sign-in {formatWhen(user.lastSignIn).toLowerCase()}</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={active}
              aria-labelledby="active-label"
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

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={busy}
            className="focus-ring h-[2.6rem] flex-1 cursor-pointer rounded-full border-[1.5px] border-crimson bg-crimson text-[0.78rem] font-bold text-white transition-colors hover:bg-crimson-hover disabled:cursor-wait disabled:opacity-60"
          >
            {user ? "Save changes" : "Create user"}
          </button>
          {user?.status === "locked" && (
            <button
              type="button"
              onClick={unlock}
              disabled={busy}
              className="focus-ring h-[2.6rem] cursor-pointer rounded-full border-[1.5px] border-[#E5E7EB] bg-white px-[1.1rem] text-[0.78rem] font-bold text-slate-ink transition-colors hover:border-crimson hover:text-crimson disabled:cursor-wait disabled:opacity-60"
            >
              Unlock
            </button>
          )}
        </div>
        <p className={muted}>
          Deactivating ends a person&apos;s session straight away. Accounts are never deleted.
          {user && ` Created ${formatDay(user.created)}.`}
        </p>
      </form>
    </Card>
  );
}
