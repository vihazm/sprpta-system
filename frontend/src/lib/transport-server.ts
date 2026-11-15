import "server-only";

import { cookies } from "next/headers";
import { ACCESS_COOKIE, API_URL } from "@/lib/auth-constants";

// How api() reaches the backend from a server component: straight to FastAPI, with the signed-in user's cookie.

export async function send(path: string, method: string, body?: unknown): Promise<Response> {
  const access = (await cookies()).get(ACCESS_COOKIE)?.value;
  return fetch(`${API_URL}${path}`, {
    method,
    headers: {
      ...(access ? { cookie: `${ACCESS_COOKIE}=${access}` } : {}),
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    cache: "no-store",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

// The proxy renews an expiring session before a page is rendered, so there is nothing to renew here.
export async function renewSession(): Promise<boolean> {
  return false;
}
