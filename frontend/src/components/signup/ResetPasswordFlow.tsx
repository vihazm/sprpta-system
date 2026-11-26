"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { FieldError } from "@/components/login/FieldError";
import { ModeToggle } from "@/components/login/ModeToggle";
import { PasswordInput } from "@/components/login/PasswordInput";
import { notify } from "@/lib/notify";
import { requestReset, resetPassword } from "@/lib/signup-client";
import {
  normaliseIdentifier,
  sanitizePhoneInput,
  validateConfirmPassword,
  validateIdentifier,
  validateNewPassword,
  type AuthMode,
} from "@/lib/validators";
import { EMPTY_CODE, OtpInput } from "./OtpInput";
import { heading, inputClass, primaryButton, textButton } from "./styles";

type Step = "account" | "reset";

/** A complainant's forgotten password: the email or number first, then the one-time code with a new password. */
export function ResetPasswordFlow() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("account");
  const [busy, setBusy] = useState(false);

  const [mode, setMode] = useState<AuthMode>("email");
  const [identifier, setIdentifier] = useState("");
  const [triedAccount, setTriedAccount] = useState(false);

  const [code, setCode] = useState(EMPTY_CODE);
  const [codeError, setCodeError] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [triedReset, setTriedReset] = useState(false);
  const [wait, setWait] = useState(0); // seconds before a new code may be asked for

  const isEmail = mode === "email";
  const identifierError = triedAccount ? validateIdentifier(mode, identifier) : "";
  const passwordErrors = {
    password: validateNewPassword(password),
    confirm: validateConfirmPassword(password, confirm),
  };
  const shown = (message: string) => (triedReset ? message : "");
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

  async function sendCode() {
    setBusy(true);
    const result = await requestReset(target);
    setBusy(false);
    if (!result.ok) {
      if (result.retryAfter) setWait(result.retryAfter);
      notify.error(result.title, result.message);
      return false;
    }
    setCode(EMPTY_CODE);
    setCodeError("");
    setWait(result.resendAfter);
    return true;
  }

  async function onAccount(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setTriedAccount(true);
    if (validateIdentifier(mode, identifier)) return;
    if (await sendCode()) setStep("reset");
  }

  async function onReset(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setTriedReset(true);
    const typed = code.join("");
    if (typed.length < 6) setCodeError("Enter the 6-digit code.");
    if (typed.length < 6 || Object.values(passwordErrors).some(Boolean)) return;

    setBusy(true);
    const result = await resetPassword(target, typed, password);
    if (result.ok) {
      notify.success("Password changed", "Sign in with your new password.");
      router.replace("/"); // stays "busy" while the sign-in page loads
      return;
    }
    setBusy(false);
    setCode(EMPTY_CODE);
    if (result.code === "invalid_code" || result.code === "too_many_codes") setCodeError(result.message);
    else notify.error(result.title, result.message);
  }

  async function onResend() {
    if (busy || wait > 0) return;
    if (await sendCode()) notify.success("New code sent", `We sent a new code to your ${isEmail ? "email" : "phone"}.`);
  }

  return (
    <section className="flex flex-col px-[2.9rem] pb-[2.1rem] pt-[2.7rem] max-[899px]:px-[1.4rem] max-[899px]:pb-[1.5rem] max-[899px]:pt-[1.7rem]">
      {step === "account" ? (
        <>
          <h2 className={heading}>Forgot your password?</h2>
          <p className="mb-0 mt-[0.6rem] text-[0.92rem] text-muted">
            Enter the email or mobile number of your complainant account. We will send you a code to set a new
            password.
          </p>

          <form noValidate onSubmit={onAccount} className="mt-[1.4rem] flex flex-col gap-[1.05rem]">
            <ModeToggle mode={mode} onChange={pickMode} label="Receive the code by" />
            <div className="flex flex-col gap-[0.4rem]">
              <label htmlFor="fp-identifier" className="text-[0.84rem] font-bold">
                {isEmail ? "Email address" : "Mobile number"}
              </label>
              <input
                id="fp-identifier"
                className={inputClass}
                type={isEmail ? "email" : "tel"}
                inputMode={isEmail ? "email" : "tel"}
                autoComplete={isEmail ? "email" : "tel"}
                placeholder={isEmail ? "name@example.com" : "07X XXX XXXX"}
                value={identifier}
                onChange={(e) => setIdentifier(isEmail ? e.target.value : sanitizePhoneInput(e.target.value))}
                aria-invalid={!!identifierError}
                aria-describedby="fp-identifier-err"
              />
              <FieldError id="fp-identifier-err" message={identifierError} />
            </div>
            <button type="submit" disabled={busy} className={`${primaryButton} mt-[0.3rem]`}>
              {busy ? "Sending code…" : "Send code"}
            </button>
          </form>

          <p className="mb-0 mt-[1.1rem] text-[0.82rem] text-muted">
            SPRPTA staff: ask the System Administrator to reset your password.
          </p>
        </>
      ) : (
        <>
          <h2 className={heading}>Set a new password</h2>
          <p className="mb-0 mt-[0.6rem] text-[0.92rem] text-muted">
            If <b className="text-ink">{identifier.trim()}</b> belongs to an account, we sent it a 6-digit code. It works
            for 10 minutes.
          </p>

          <form noValidate onSubmit={onReset} className="mt-[1.5rem] flex flex-col gap-[0.9rem]">
            <OtpInput
              value={code}
              onChange={(update) => {
                setCode(update);
                setCodeError("");
              }}
              invalid={!!codeError}
              disabled={busy}
              describedBy="fp-code-err"
            />
            <FieldError id="fp-code-err" message={codeError} />

            <div className="flex flex-col gap-[0.4rem]">
              <label htmlFor="fp-password" className="text-[0.84rem] font-bold">
                New password
              </label>
              <PasswordInput
                id="fp-password"
                value={password}
                onChange={setPassword}
                autoComplete="new-password"
                placeholder="At least 8 characters"
                invalid={!!shown(passwordErrors.password)}
                describedBy="fp-password-err"
              />
              <FieldError id="fp-password-err" message={shown(passwordErrors.password)} />
            </div>
            <div className="flex flex-col gap-[0.4rem]">
              <label htmlFor="fp-confirm" className="text-[0.84rem] font-bold">
                Confirm new password
              </label>
              <PasswordInput
                id="fp-confirm"
                value={confirm}
                onChange={setConfirm}
                autoComplete="new-password"
                placeholder="Type it again"
                invalid={!!shown(passwordErrors.confirm)}
                describedBy="fp-confirm-err"
              />
              <FieldError id="fp-confirm-err" message={shown(passwordErrors.confirm)} />
            </div>

            <button type="submit" disabled={busy} className={`${primaryButton} mt-[0.5rem]`}>
              {busy ? "Saving…" : "Change password"}
            </button>
          </form>

          <div className="mt-[1.1rem] flex items-center justify-between gap-3">
            <button type="button" className={textButton} disabled={busy} onClick={() => setStep("account")}>
              Use a different {isEmail ? "email" : "number"}
            </button>
            <button type="button" className={textButton} disabled={busy || wait > 0} onClick={onResend}>
              {wait > 0 ? `Resend code in ${wait}s` : "Resend code"}
            </button>
          </div>
        </>
      )}

      <p className="mb-0 mt-[1.4rem] border-t border-[#efe9eb] pt-[1rem] text-center text-[0.86rem] text-muted">
        Remembered it?{" "}
        <Link href="/" className="focus-ring rounded-sm font-bold text-crimson hover:underline">
          Back to sign in
        </Link>
      </p>
    </section>
  );
}
