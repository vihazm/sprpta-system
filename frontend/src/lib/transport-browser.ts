// How api() reaches the backend from the browser: through Next.js at /api, with the session cookie.

// A FormData body (a file upload) is sent as it is: the browser adds its own content type.
export function send(path: string, method: string, body?: unknown) {
  const upload = body instanceof FormData;
  return fetch(path, {
    method,
    headers: body === undefined || upload ? undefined : { "Content-Type": "application/json" },
    credentials: "same-origin",
    cache: "no-store",
    body: body === undefined || upload ? (body as FormData | undefined) : JSON.stringify(body),
  });
}

export async function renewSession(): Promise<boolean> {
  try {
    return (await fetch("/api/auth/refresh", { method: "POST", credentials: "same-origin" })).ok;
  } catch {
    return false;
  }
}
