import "server-only";

import { cookies } from "next/headers";
import { ACCESS_COOKIE, API_URL } from "@/lib/auth-constants";
import { toSystemHealth } from "./api";
import type { SystemHealthData } from "./types";

/**
 * The readings behind the System health page, for the signed-in administrator.
 * Returns null when the backend cannot be reached or says no.
 */
export async function getSystemHealth(): Promise<SystemHealthData | null> {
  const access = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (!access) return null;

  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/admin/system-health`, {
      headers: { cookie: `${ACCESS_COOKIE}=${access}` },
      cache: "no-store",
    });
  } catch {
    return null;
  }
  return res.ok ? toSystemHealth(await res.json()) : null;
}
