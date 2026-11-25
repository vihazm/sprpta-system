"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { FieldError } from "@/components/login/FieldError";
import { ModeToggle } from "@/components/login/ModeToggle";
import { PasswordInput } from "@/components/login/PasswordInput";
import { notify } from "@/lib/notify";
import { resendCode, signUp, verifyCode } from "@/lib/signup-client";
import {
  normaliseIdentifier,
  sanitizePhoneInput,
  validateConfirmPassword,
  validateIdentifier,
  validateName,
  validateNewPassword,
  type AuthMode,
} from "@/lib/validators";
import { EMPTY_CODE, OtpInput } from "./OtpInput";

const inputClass =
  "h-[3.1rem] w-full rounded-[0.95rem] border-[1.5px] border-[#e4dde0] bg-field px-[1.05rem] text-[0.96rem] font-medium text-ink outline-none transition placeholder:text-[#6F7682] focus:border-crimson focus:bg-white focus:shadow-[0_0_0_0.25rem_rgba(179,17,47,0.12)] aria-[invalid=true]:border-error aria-[invalid=true]:bg-[#FFF6F5]";
const primaryButton =
  "focus-ring flex h-[3.3rem] w-full cursor-pointer items-center justify-center rounded-2xl bg-crimson text-base font-bold text-white shadow-[0_14px_26px_-12px_rgba(179,17,47,0.85)] transition hover:bg-crimson-hover active:translate-y-px disabled:cursor-wait disabled:opacity-70";
const textButton =
  "focus-ring cursor-pointer rounded-sm border-0 bg-transparent p-0 text-[0.86rem] font-bold text-crimson hover:text-crimson-link-hover disabled:cursor-default disabled:text-muted";
const heading = "m-0 font-display text-[2.1rem] leading-[1.12] tracking-[-0.03em] max-[599px]:text-[1.8rem]";

type Step = "details" | "code";

/** The complainant sign-up: details first, then the one-time code. A correct code signs the person in. */
export function SignUpFlow() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("details");
  const [busy, setBusy] = useState(false);

  const [mode, setMode] = useState<AuthMode>("email");
  const [name, setName] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [tried, setTried] = useState(false);

  const [code, setCode] = useState(EMPTY_CODE);
  const [codeError, setCodeError] = useState("");
  const [wait, setWait] = useState(0); // seconds before a new code may be asked for

  const isEmail = mode === "email";
  const errors = {
    name: validateName(name),
    identifier: validateIdentifier(mode, identifier),
    password: validateNewPassword(password),
    confirm: validateConfirmPassword(password, confirm),
  };
  const shown = (message: string) => (tried ? message : "");
  const target = normaliseIdentifier(mode, identifier);

  useEffect(() => {
    if (wait <= 0) return;
    const timer = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(timer);
  }, [wait]);

  function pickMode(next: AuthMode) {
    if (next === mode) return;
    setMode(next);
    setIdentifier("");
  }

  async function onDetails(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setTried(true);
    if (Object.values(errors).some(Boolean)) return;

    setBusy(true);
    const result = await signUp(name.trim(), target, password);
    setBusy(false);
    if (!result.ok) return notify.error(result.title, result.message);
    setCode(EMPTY_CODE);
    setCodeError("");
    setWait(result.resendAfter);
    setStep("code");
  }

  async function onCode(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    const typed = code.join("");
    if (typed.length < 6) return setCodeError("Enter the 6-digit code.");

    setBusy(true);
    const result = await verifyCode(target, typed);
    if (result.ok) {
      notify.success("Account ready", `Welcome, ${result.name}.`);
      router.replace(result.redirectTo); // stays "busy" while the portal loads
      return;
    }
    setBusy(false);
    setCode(EMPTY_CODE);
    if (result.code === "invalid_code" || result.code === "too_many_codes") setCodeError(result.message);
    else notify.error(result.title, result.message);
  }

  async function onResend() {
    if (busy || wait > 0) return;
    setBusy(true);
    const result = await resendCode(target);
    setBusy(false);
    if (!result.ok) {
      if (result.retryAfter) setWait(result.retryAfter);
      return notify.error(result.title, result.message);
    }
    setCode(EMPTY_CODE);
    setCodeError("");
    setWait(result.resendAfter);
    notify.success("New code sent", `We sent a new code to your ${isEmail ? "email" : "phone"}.`);
  }

  return (
    <section className="flex flex-col px-[2.9rem] pb-[2.1rem] pt-[2.7rem] max-[899px]:px-[1.4rem] max-[899px]:pb-[1.5rem] max-[899px]:pt-[1.7rem]">
      <ol className="m-0 mb-[1.6rem] flex list-none items-center gap-[0.6rem] p-0 text-[0.78rem] font-bold" aria-label="Sign-up progress">
        {["Your details", "Verify code"].map((label, i) => {
          const current = step === "details" ? 0 : 1;
          const active = current >= i;
          return (
            <li key={label} aria-current={current === i ? "step" : undefined} className="flex items-center gap-[0.6rem]">
              {i > 0 && <span className={`h-[2px] w-[2.2rem] ${active ? "bg-crimson" : "bg-[#e5e1e3]"}`} />}
              <span
                className={`grid size-[1.65rem] place-items-center rounded-full text-[0.74rem] font-extrabold ${
                  active ? "bg-crimson text-white" : "bg-[#e9e4e6] text-muted"
                }`}
              >
                {i + 1}
              </span>
              <span className={active ? "text-crimson" : "text-muted"}>{label}</span>
            </li>
          );
        })}
      </ol>
      {step === "details" ? (
        <>
          <h2 className={heading}>Create your account</h2>
          <p className="mb-0 mt-[0.6rem] text-[0.92rem] text-muted">
            One account lets you lodge complaints and watch them move to a result.
          </p>

          <form noValidate onSubmit={onDetails} className="mt-[1.4rem] flex flex-col gap-[1.05rem]">
            <div className="flex flex-col gap-[0.4rem]">
              <label htmlFor="su-name" className="text-[0.84rem] font-bold">
                Full name
              </label>
              <input
                id="su-name"
                className={inputClass}
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                aria-invalid={!!shown(errors.name)}
                aria-describedby="su-name-err"
              />
              <FieldError id="su-name-err" message={shown(errors.name)} />
            </div>

            <div className="flex flex-col gap-[0.4rem]">
              <span className="text-[0.84rem] font-bold">How should we reach you?</span>
              <ModeToggle mode={mode} onChange={pickMode} label="Receive the code by" />
            </div>

            <div className="flex flex-col gap-[0.4rem]">
              <label htmlFor="su-identifier" className="text-[0.84rem] font-bold">
                {isEmail ? "Email address" : "Mobile number"}
              </label>
              <input
                id="su-identifier"
                className={inputClass}
                type={isEmail ? "email" : "tel"}
                inputMode={isEmail ? "email" : "tel"}
                autoComplete={isEmail ? "email" : "tel"}
                placeholder={isEmail ? "name@example.com" : "07X XXX XXXX"}
                value={identifier}
                onChange={(e) => setIdentifier(isEmail ? e.target.value : sanitizePhoneInput(e.target.value))}
                aria-invalid={!!shown(errors.identifier)}
                aria-describedby="su-identifier-err"
              />
              <FieldError id="su-identifier-err" message={shown(errors.identifier)} />
            </div>

            <div className="grid grid-cols-2 gap-[0.8rem] max-[599px]:grid-cols-1">
              <div className="flex flex-col gap-[0.4rem]">
                <label htmlFor="su-password" className="text-[0.84rem] font-bold">
                  Password
                </label>
                <PasswordInput
                  id="su-password"
                  value={password}
                  onChange={setPassword}
                  autoComplete="new-password"
                  placeholder="At least 8 characters"
                  invalid={!!shown(errors.password)}
                  describedBy="su-password-err"
                />
                <FieldError id="su-password-err" message={shown(errors.password)} />
              </div>
              <div className="flex flex-col gap-[0.4rem]">
                <label htmlFor="su-confirm" className="text-[0.84rem] font-bold">
                  Confirm password
                </label>
                <PasswordInput
                  id="su-confirm"
                  value={confirm}
                  onChange={setConfirm}
                  autoComplete="new-password"
                  placeholder="Type it again"
                  invalid={!!shown(errors.confirm)}
                  describedBy="su-confirm-err"
                />
                <FieldError id="su-confirm-err" message={shown(errors.confirm)} />
              </div>
            </div>

            <button type="submit" disabled={busy} className={`${primaryButton} mt-[0.3rem]`}>
              {busy ? "Sending code…" : "Continue"}
            </button>
          </form>

          <p className="mb-0 mt-[1.1rem] text-center text-[0.86rem] text-muted">
            Already registered?{" "}
            <Link href="/" className="focus-ring rounded-sm font-bold text-crimson hover:underline">
              Sign in
            </Link>
          </p>
        </>
      ) : (
        <>
          <h2 className={heading}>Enter the code</h2>
          <p className="mb-0 mt-[0.6rem] text-[0.92rem] text-muted">
            We sent a 6-digit code to <b className="text-ink">{identifier.trim()}</b>. It works for 10 minutes.
          </p>

          <form noValidate onSubmit={onCode} className="mt-[1.5rem] flex flex-col gap-[0.9rem]">
            <OtpInput
              value={code}
              onChange={(update) => {
                setCode(update);
                setCodeError("");
              }}
              invalid={!!codeError}
              disabled={busy}
              describedBy="su-code-err"
            />
            <FieldError id="su-code-err" message={codeError} />
            <button type="submit" disabled={busy} className={`${primaryButton} mt-[0.5rem]`}>
              {busy ? "Checking…" : "Verify and continue"}
            </button>
          </form>

          <div className="mt-[1.1rem] flex items-center justify-between gap-3">
            <button type="button" className={textButton} disabled={busy} onClick={() => setStep("details")}>
              Use a different {isEmail ? "email" : "number"}
            </button>
            <button type="button" className={textButton} disabled={busy || wait > 0} onClick={onResend}>
              {wait > 0 ? `Resend code in ${wait}s` : "Resend code"}
            </button>
          </div>
        </>
      )}
      <p className="mb-0 mt-[1.4rem] flex items-center justify-center gap-[0.4rem] border-t border-[#efe9eb] pt-[1rem] text-center text-[0.74rem] text-muted">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="4" y="10.5" width="16" height="10" rx="2.5" />
          <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" />
        </svg>
        Your details are used only to contact you about your complaints.
      </p>
    </section>
  );
}
