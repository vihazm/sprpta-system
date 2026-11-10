// Browser-side calls to the backend for signed-in pages. The access token lives in a
// 15 minute cookie, so a page left open can find it expired: the call then renews the
// session once and retries before giving up.

export type ApiResult<T> = { ok: true; data: T } | { ok: false; message: string };

const NETWORK_ERROR = "Can't reach the server. Check your connection and try again.";
const SERVER_ERROR = "Something went wrong on our side. Please try again in a moment.";

function send(path: string, method: string, body?: unknown) {
  return fetch(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    credentials: "same-origin",
    cache: "no-store",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function renewSession(): Promise<boolean> {
  try {
    return (await fetch("/api/auth/refresh", { method: "POST", credentials: "same-origin" })).ok;
  } catch {
    return false;
  }
}

export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<ApiResult<T>> {
  const method = options.method ?? "GET";
  let res: Response;
  try {
    res = await send(path, method, options.body);
    if (res.status === 401 && (await renewSession())) {
      res = await send(path, method, options.body);
    }
  } catch {
    return { ok: false, message: NETWORK_ERROR };
  }

  const body = await res.json().catch(() => null);
  if (res.ok) return { ok: true, data: body as T };
  if (res.status >= 500) return { ok: false, message: SERVER_ERROR };

  // Our own errors carry a readable message; validation errors arrive as a list.
  const message = typeof body?.detail?.message === "string" ? body.detail.message : null;
  return { ok: false, message: message ?? "Please check the details and try again." };
}
