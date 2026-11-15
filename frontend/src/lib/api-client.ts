// Calls to the backend for signed-in pages. In the browser the access token lives in a
// 15 minute cookie, so a page left open can find it expired: the call then renews the
// session once and retries before giving up. Server components use the same functions to
// read a page's data before the page is sent (see the "#transport" import in package.json).

import { renewSession, send } from "#transport";

export type ApiResult<T> = { ok: true; data: T } | { ok: false; message: string; status?: number };

const NETWORK_ERROR = "Can't reach the server. Check your connection and try again.";
const SERVER_ERROR = "Something went wrong on our side. Please try again in a moment.";

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
  if (res.status >= 500) return { ok: false, message: SERVER_ERROR, status: res.status };

  // Our own errors carry a readable message; validation errors arrive as a list.
  const message = typeof body?.detail?.message === "string" ? body.detail.message : null;
  return { ok: false, message: message ?? "Please check the details and try again.", status: res.status };
}
