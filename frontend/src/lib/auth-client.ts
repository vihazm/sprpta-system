// Browser-side calls to the auth API. Tokens live in httpOnly cookies set by
// the backend, so nothing secret is ever visible to this code.

import { isRole, type Role } from "@/lib/roles";

export type SignInResult =
  | { ok: true; role: Role; name: string; redirectTo: string }
  | { ok: false; title: string; message: string; code?: string; retryAfter?: number };

// Short headline for each backend error code, shown in the notification pill.
const ERROR_TITLES: Record<string, string> = {
  invalid_credentials: "Sign-in failed",
  account_locked: "Account locked",
  too_many_attempts: "Too many attempts",
  account_disabled: "Account deactivated",
  account_not_verified: "Account not verified",
};
const NETWORK_ERROR = {
  title: "No connection",
  message: "Can't reach the server. Check your connection and try again.",
};
const SERVER_ERROR = {
  title: "Server problem",
  message: "Something went wrong on our side. Please try again in a moment.",
};

export const AUTH_CHANNEL = "sprpta-auth";

export async function signIn(identifier: string, password: string): Promise<SignInResult> {
  let res: Response;
  try {
    res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ identifier, password }),
    });
  } catch {
    return { ok: false, ...NETWORK_ERROR };
  }

  const body = await res.json().catch(() => null);
  if (res.ok && isRole(body?.user?.role) && typeof body?.redirect_to === "string") {
    return {
      ok: true,
      role: body.user.role,
      name: String(body.user.name ?? ""),
      redirectTo: body.redirect_to,
    };
  }
  if (res.status >= 500) return { ok: false, ...SERVER_ERROR };
  if (!body?.detail?.message) {
    return { ok: false, title: "Sign-in failed", message: "Please check your details and try again." };
  }
  return {
    ok: false,
    title: ERROR_TITLES[body.detail.code] ?? "Sign-in failed",
    message: body.detail.message,
    code: body.detail.code,
    retryAfter: body.detail.retry_after,
  };
}

/** Ends this browser's session, tells other open tabs, and returns to the login page. */
export async function signOut(): Promise<void> {
  try {
    await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
  } catch {
    // Even if the request failed, leave: the session ends by timeout anyway.
  }
  try {
    const channel = new BroadcastChannel(AUTH_CHANNEL);
    channel.postMessage("logout");
    channel.close();
  } catch {
    // BroadcastChannel unavailable: other tabs will notice on their next request.
  }
  // A full navigation (not router.push) drops every cached page.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- full page load on purpose
  window.location.assign("/?reason=signed-out");
}
