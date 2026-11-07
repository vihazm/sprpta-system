export type AuthMode = "email" | "phone";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const PHONE_RE = /^(?:0|\+94|94)?7\d{8}$/;

/** Removes characters a phone number can't contain (keeps digits, +, space, -). */
export function sanitizePhoneInput(value: string): string {
  return value.replace(/[^\d+\s-]/g, "");
}

/** Returns an error message, or "" when the identifier is valid. */
export function validateIdentifier(mode: AuthMode, raw: string): string {
  const value = raw.trim();
  if (!value) {
    return mode === "email"
      ? "Enter your email address."
      : "Enter your phone number.";
  }
  if (mode === "email") {
    return EMAIL_RE.test(value)
      ? ""
      : "Enter a valid email address, like name@example.com.";
  }
  const digits = value.replace(/[\s-]/g, "");
  return PHONE_RE.test(digits)
    ? ""
    : "Enter a valid mobile number, like 071 234 5678.";
}

/** Login only requires a password; no length or complexity rule here. */
export function validatePassword(value: string): string {
  return value ? "" : "Enter your password.";
}

/** Email: trimmed + lower-cased. Phone: +947XXXXXXXXX. (Backend format still to be confirmed.) */
export function normaliseIdentifier(mode: AuthMode, raw: string): string {
  const value = raw.trim();
  if (mode === "email") return value.toLowerCase();
  const digits = value.replace(/[\s-]/g, "");
  const national = digits.replace(/^(?:0|\+94|94)/, "");
  return `+94${national}`;
}
