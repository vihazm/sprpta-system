import "server-only";

import { cookies } from "next/headers";
import { ACCESS_COOKIE, API_URL } from "@/lib/auth-constants";
import { toSummary } from "./api";
import type { UsersSummary } from "./types";

/**
 * The figures above the directory and the area coverage, read for the signed-in
 * administrator. Returns null when the backend cannot be reached or says no.
 */
export async function getUsersSummary(): Promise<UsersSummary | null> {
  const access = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (!access) return null;

  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/admin/users/summary`, {
      headers: { cookie: `${ACCESS_COOKIE}=${access}` },
      cache: "no-store",
    });
  } catch {
    return null;
  }
  return res.ok ? toSummary(await res.json()) : null;
}
