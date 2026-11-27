// Browser-side calls for the complainant sign-up (send a code, ask for a new one, check the code) and for a
// forgotten password (ask for a code, then set a new password with it). The session cookies are set by the backend
// when a sign-up code is accepted.

import { isRole, type Role } from "@/lib/roles";

export type CodeSent = { channel: "email" | "sms"; resendAfter: number };

type Failure = { ok: false; title: string; message: string; code?: string; retryAfter?: number };

const TITLES: Record<string, string> = {
  already_registered: "Already registered",
  invalid_code: "Code not accepted",
  too_many_codes: "Too many wrong codes",
  resend_too_soon: "Please wait",
  too_many_attempts: "Too many attempts",
  code_not_sent: "Code not sent",
  no_pending_signup: "Sign-up not found",
  staff_account: "Staff account",
};

async function post(path: string, body: unknown): Promise<{ res: Response; data: unknown } | Failure> {
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
    return { res, data: await res.json().catch(() => null) };
  } catch {
    return {
      ok: false,
      title: "No connection",
      message: "Can't reach the server. Check your connection and try again.",
    };
  }
}

function failure(res: Response, data: unknown): Failure {
  const detail = (data as { detail?: { code?: string; message?: string; retry_after?: number } } | null)?.detail;
  if (res.status >= 500 && res.status !== 503) {
    return {
      ok: false,
      title: "Server problem",
      message: "Something went wrong on our side. Please try again in a moment.",
    };
  }
  if (typeof detail?.message !== "string") {
    return { ok: false, title: "Could not continue", message: "Please check your details and try again." };
  }
  return {
    ok: false,
    title: TITLES[detail.code ?? ""] ?? "Could not continue",
    message: detail.message,
    code: detail.code,
    retryAfter: detail.retry_after,
  };
}

async function sendCode(path: string, body: unknown): Promise<({ ok: true } & CodeSent) | Failure> {
  const result = await post(path, body);
  if ("ok" in result) return result;
  const sent = result.data as { channel?: "email" | "sms"; resend_after?: number } | null;
  if (result.res.ok && sent?.channel) {
    return { ok: true, channel: sent.channel, resendAfter: sent.resend_after ?? 60 };
  }
  return failure(result.res, result.data);
}

export function signUp(name: string, identifier: string, password: string) {
  return sendCode("/api/auth/signup", { name, identifier, password });
}

export function resendCode(identifier: string) {
  return sendCode("/api/auth/resend-otp", { identifier });
}

export async function verifyCode(
  identifier: string,
  code: string,
): Promise<{ ok: true; role: Role; name: string; redirectTo: string } | Failure> {
  const result = await post("/api/auth/verify-otp", { identifier, code });
  if ("ok" in result) return result;
  const body = result.data as { user?: { role?: unknown; name?: unknown }; redirect_to?: unknown } | null;
  if (result.res.ok && isRole(body?.user?.role) && typeof body?.redirect_to === "string") {
    return { ok: true, role: body.user.role, name: String(body.user.name ?? ""), redirectTo: body.redirect_to };
  }
  return failure(result.res, result.data);
}

export function requestReset(identifier: string) {
  return sendCode("/api/auth/forgot-password", { identifier });
}

export async function resetPassword(identifier: string, code: string, password: string): Promise<{ ok: true } | Failure> {
  const result = await post("/api/auth/reset-password", { identifier, code, password });
  if ("ok" in result) return result;
  return result.res.ok ? { ok: true } : failure(result.res, result.data);
}

/** Refuses a staff email or phone number before the sign-in page opens Create account or Forgot password. */
export async function checkNotStaff(identifier: string): Promise<{ ok: true } | Failure> {
  const result = await post("/api/auth/account-check", { identifier });
  if ("ok" in result) return result;
  return result.res.ok ? { ok: true } : failure(result.res, result.data);
}
