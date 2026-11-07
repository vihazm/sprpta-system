"use client";

import Link from "next/link";
import { useState, type FormEvent, type ReactNode } from "react";
import {
  sanitizePhoneInput,
  validateIdentifier,
  validatePassword,
  type AuthMode,
} from "@/lib/validators";
import { FieldError } from "./FieldError";

const inputClass =
  "h-[3.1rem] w-full rounded-[0.95rem] border-[1.5px] border-transparent bg-field px-[1.05rem] text-[0.96rem] font-medium text-ink outline-none transition placeholder:text-[#6F7682] focus:border-crimson focus:bg-white focus:shadow-[0_0_0_0.25rem_rgba(179,17,47,0.12)] aria-[invalid=true]:border-error aria-[invalid=true]:bg-[#FFF6F5]";

export function LoginSheet() {
  const [mode, setMode] = useState<AuthMode>("email");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [identifierTouched, setIdentifierTouched] = useState(false);
  const [passwordTouched, setPasswordTouched] = useState(false);
  const [notice, setNotice] = useState("");

  const isEmail = mode === "email";
  const identifierError = identifierTouched
    ? validateIdentifier(mode, identifier)
    : "";
  const passwordError = passwordTouched ? validatePassword(password) : "";

  function pickMode(next: AuthMode) {
    if (next === mode) return;
    setMode(next);
    setIdentifier("");
    setIdentifierTouched(false);
    setNotice("");
  }

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIdentifierTouched(true);
    setPasswordTouched(true);
    if (validateIdentifier(mode, identifier) || validatePassword(password)) {
      setNotice("");
      return;
    }
    // Front end only for now: no backend call yet.
    setNotice("Sign-in is not connected to the server yet.");
  }

  return (
    <div className="w-full max-w-[28rem] rounded-[1.9rem] bg-white px-[2.1rem] pb-[1.6rem] pt-[2.2rem] shadow-[0_1px_2px_rgba(60,20,30,0.05),0_30px_60px_-28px_rgba(110,8,30,0.3),0_0_0_1px_rgba(60,20,30,0.04)] max-[899px]:px-[1.4rem] max-[899px]:pb-[1.3rem] max-[899px]:pt-[1.7rem]">
      <h1 className="m-0 text-[2.1rem] font-extrabold leading-[1.1] tracking-[-0.03em]">
        Welcome back
      </h1>
      <p className="mb-0 mt-[0.4rem] text-[0.95rem] text-muted">
        Sign in to continue to SPRPTA.
      </p>

      <form
        noValidate
        onSubmit={onSubmit}
        className="mt-[1.35rem] flex flex-col gap-[1.1rem]"
      >
        <div
          role="group"
          aria-label="Sign in with"
          className="relative grid grid-cols-2 rounded-full bg-field p-[0.3rem]"
        >
          <span
            aria-hidden="true"
            className={`absolute bottom-[0.3rem] left-[0.3rem] top-[0.3rem] w-[calc(50%-0.3rem)] rounded-full bg-ink transition-transform duration-[280ms] ease-[cubic-bezier(.3,.9,.3,1)] ${
              isEmail ? "" : "translate-x-full"
            }`}
          />
          <ToggleButton
            active={isEmail}
            label="Email"
            onClick={() => pickMode("email")}
          >
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.9"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <rect x="3" y="5" width="18" height="14" rx="2.5" />
              <path d="M3.5 7l8.5 6 8.5-6" />
            </svg>
          </ToggleButton>
          <ToggleButton
            active={!isEmail}
            label="Phone"
            onClick={() => pickMode("phone")}
          >
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.9"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <rect x="7" y="2.5" width="10" height="19" rx="2.5" />
              <path d="M11 18.5h2" />
            </svg>
          </ToggleButton>
        </div>

        <div className="flex flex-col gap-[0.45rem]">
          <label
            htmlFor="login-identifier"
            className="text-[0.84rem] font-bold"
          >
            {isEmail ? "Email address" : "Phone number"}
          </label>
          <input
            id="login-identifier"
            className={inputClass}
            type={isEmail ? "email" : "tel"}
            inputMode={isEmail ? "email" : "tel"}
            placeholder={isEmail ? "name@example.com" : "07X XXX XXXX"}
            autoComplete="username"
            value={identifier}
            onChange={(e) => {
              setIdentifier(
                isEmail ? e.target.value : sanitizePhoneInput(e.target.value),
              );
              setNotice("");
            }}
            onBlur={() => setIdentifierTouched(true)}
            aria-invalid={!!identifierError}
            aria-describedby="login-identifier-err"
          />
          <FieldError id="login-identifier-err" message={identifierError} />
        </div>

        <div className="flex flex-col gap-[0.45rem]">
          <div className="flex items-center justify-between">
            <label htmlFor="login-password" className="text-[0.84rem] font-bold">
              Password
            </label>
            <Link
              href="/forgot-password"
              className="focus-ring rounded-sm text-[0.8rem] font-bold text-crimson hover:underline"
            >
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <input
              id="login-password"
              className={`${inputClass} pr-16`}
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setNotice("");
              }}
              onBlur={() => setPasswordTouched(true)}
              aria-invalid={!!passwordError}
              aria-describedby="login-password-err"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="focus-ring absolute right-[0.3rem] top-[0.3rem] h-[2.4rem] min-w-[2.9rem] cursor-pointer rounded-[0.6rem] bg-transparent text-[0.78rem] font-bold text-muted"
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
          <FieldError id="login-password-err" message={passwordError} />
        </div>

        <button
          type="submit"
          className="focus-ring group flex h-[3.3rem] cursor-pointer items-center justify-center gap-[0.55rem] rounded-2xl bg-crimson text-base font-bold text-white shadow-[0_14px_26px_-12px_rgba(179,17,47,0.85)] transition hover:bg-crimson-hover active:translate-y-px"
        >
          Sign in
          <svg
            width="17"
            height="17"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#fff"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="transition-transform group-hover:translate-x-[3px]"
          >
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </button>

        <div role="status" aria-live="polite">
          {notice && (
            <p className="m-0 text-center text-[0.8rem] font-semibold text-muted">
              {notice}
            </p>
          )}
        </div>
      </form>

      <Link
        href="/signup"
        className="focus-ring mt-[1.1rem] flex h-12 items-center justify-center gap-[0.4rem] rounded-2xl border-[1.5px] border-[#E5E7EB] text-[0.86rem] font-medium text-muted transition-colors hover:border-crimson"
      >
        New complainant?
        <b className="font-bold text-crimson">Create an account</b>
      </Link>

      <p className="mb-0 mt-[0.9rem] text-center text-[0.76rem] leading-[1.4] text-[#8A909B]">
        SPRPTA staff accounts are created by the System Administrator.
      </p>
    </div>
  );
}

function ToggleButton({
  active,
  label,
  onClick,
  children,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`focus-ring relative z-10 flex h-[2.6rem] cursor-pointer items-center justify-center gap-2 rounded-full text-[0.92rem] font-bold transition-colors duration-200 ${
        active ? "text-white" : "text-muted"
      }`}
    >
      {children}
      {label}
    </button>
  );
}
