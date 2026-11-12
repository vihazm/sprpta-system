import { NextResponse, type NextRequest } from "next/server";
import {
  ACCESS_COOKIE,
  API_URL,
  REFRESH_COOKIE,
  REFRESH_COOKIE_PATH,
} from "@/lib/auth-constants";
import { LANDING_PATH, isRole, roleForPath, safeNextPath } from "@/lib/roles";

/**
 * Optimistic route guard plus silent token renewal.
 *
 * - Role pages: with no session cookie, go to the login page. When the access
 *   token has expired, quietly swap the refresh token for a new one (cookies
 *   can only be set here, not in server components).
 * - Role pages: a user in another role's area is sent to their own landing page
 *   before anything is rendered, so the other area's page is never streamed.
 * - Login page ("/"): a signed-in user is sent straight to their own area.
 *
 * This is not the security boundary. The token is only decoded here, not
 * verified. Server components re-check the session with the backend
 * (lib/session.ts) and the backend checks every API call.
 */

type Renewed = { setCookies: string[]; access: string | null; refresh: string | null };

function readToken(token: string | undefined): { exp?: number; role?: string } | null {
  if (!token) return null;
  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

function isFresh(token: string | undefined): boolean {
  const exp = readToken(token)?.exp;
  return typeof exp === "number" && exp * 1000 > Date.now() + 5_000;
}

/** A redirect to the user's own landing page when this path is another role's area. */
function wrongArea(request: NextRequest, token: string | undefined): NextResponse | null {
  const role = readToken(token)?.role;
  const area = roleForPath(request.nextUrl.pathname);
  if (!isRole(role) || area === null || area === role) return null;
  return NextResponse.redirect(new URL(`${LANDING_PATH[role]}?denied=1`, request.url));
}

function cookieValue(setCookie: string): [string, string] {
  const pair = setCookie.split(";")[0];
  const i = pair.indexOf("=");
  return [pair.slice(0, i), pair.slice(i + 1)];
}

async function renew(refreshToken: string): Promise<Renewed | null> {
  try {
    const res = await fetch(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { cookie: `${REFRESH_COOKIE}=${refreshToken}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const setCookies = res.headers.getSetCookie();
    const values = new Map(setCookies.map(cookieValue));
    return {
      setCookies,
      access: values.get(ACCESS_COOKIE) ?? null,
      refresh: values.get(REFRESH_COOKIE) ?? null,
    };
  } catch {
    return null;
  }
}

/** Continue to the page, with renewed cookies visible to it and sent to the browser. */
function proceedWith(request: NextRequest, renewed: Renewed): NextResponse {
  const jar = new Map(
    (request.headers.get("cookie") ?? "")
      .split(/;\s*/)
      .filter(Boolean)
      .map((c) => {
        const i = c.indexOf("=");
        return [c.slice(0, i), c.slice(i + 1)] as [string, string];
      }),
  );
  if (renewed.access) jar.set(ACCESS_COOKIE, renewed.access);
  if (renewed.refresh) jar.set(REFRESH_COOKIE, renewed.refresh);
  const headers = new Headers(request.headers);
  headers.set("cookie", [...jar].map(([k, v]) => `${k}=${v}`).join("; "));

  const response = NextResponse.next({ request: { headers } });
  renewed.setCookies.forEach((c) => response.headers.append("set-cookie", c));
  return response;
}

function clearAuthCookies(response: NextResponse): NextResponse {
  response.cookies.set({ name: ACCESS_COOKIE, value: "", path: "/", maxAge: 0 });
  response.cookies.set({
    name: REFRESH_COOKIE,
    value: "",
    path: REFRESH_COOKIE_PATH,
    maxAge: 0,
  });
  return response;
}

function toLogin(request: NextRequest, reason?: string): NextResponse {
  const url = new URL("/", request.url);
  if (reason) url.searchParams.set("reason", reason);
  else url.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  return NextResponse.redirect(url);
}

async function guardRolePage(request: NextRequest): Promise<NextResponse> {
  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;

  if (isFresh(access)) return wrongArea(request, access) ?? NextResponse.next();
  if (!access && !refresh) return toLogin(request);

  const renewed = refresh ? await renew(refresh) : null;
  if (renewed) {
    const away = wrongArea(request, renewed.access ?? undefined);
    if (away) {
      renewed.setCookies.forEach((c) => away.headers.append("set-cookie", c));
      return away;
    }
    return proceedWith(request, renewed);
  }
  return clearAuthCookies(toLogin(request, "expired"));
}

async function handleLoginPage(request: NextRequest): Promise<NextResponse> {
  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;
  if (!access && !refresh) return NextResponse.next();

  let token = access;
  let renewed: Renewed | null = null;
  if (!isFresh(token) && refresh) {
    renewed = await renew(refresh);
    token = renewed?.access ?? undefined;
  }

  if (token) {
    try {
      const me = await fetch(`${API_URL}/api/auth/me`, {
        headers: { cookie: `${ACCESS_COOKIE}=${token}` },
        cache: "no-store",
      });
      if (me.ok) {
        const role = (await me.json())?.user?.role;
        if (isRole(role)) {
          const target =
            safeNextPath(request.nextUrl.searchParams.get("next"), role) ?? LANDING_PATH[role];
          const response = NextResponse.redirect(new URL(target, request.url));
          renewed?.setCookies.forEach((c) => response.headers.append("set-cookie", c));
          return response;
        }
      }
    } catch {
      return NextResponse.next(); // backend unreachable: just show the form
    }
  }
  // Stale or revoked cookies: drop them and show the login form.
  return clearAuthCookies(NextResponse.next());
}

export async function proxy(request: NextRequest) {
  return request.nextUrl.pathname === "/"
    ? handleLoginPage(request)
    : guardRolePage(request);
}

export const config = {
  matcher: ["/", "/l1/:path*", "/l2/:path*", "/l3/:path*", "/admin/:path*", "/is/:path*", "/cp/:path*"],
};
