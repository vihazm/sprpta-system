// Shared by server components and the proxy (no "server-only" here on purpose).

export const ACCESS_COOKIE = "sprpta_at";
export const REFRESH_COOKIE = "sprpta_rt";

// Path the browser only sends the refresh cookie to (matches the backend).
export const REFRESH_COOKIE_PATH = "/api/auth";

// The FastAPI backend, reached server to server. The browser never calls it
// directly: it goes through Next.js at /api (see next.config.ts rewrites).
export const API_URL = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
