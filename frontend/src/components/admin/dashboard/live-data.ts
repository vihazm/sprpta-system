import "server-only";

import { cookies } from "next/headers";
import { ACCESS_COOKIE, API_URL } from "@/lib/auth-constants";
import { toHealthService } from "../system-health/api";
import { heroServices } from "../system-health/status";
import type { LiveDashboardData } from "./types";

/**
 * The dashboard figures the backend can already answer, read for the signed-in
 * administrator. Returns null when the backend cannot be reached or says no.
 */
export async function getLiveData(): Promise<LiveDashboardData | null> {
  const access = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (!access) return null;

  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/admin/dashboard`, {
      headers: { cookie: `${ACCESS_COOKIE}=${access}` },
      cache: "no-store",
    });
  } catch {
    return null;
  }
  if (!res.ok) return null;

  // The API uses snake_case, the components use camelCase.
  const body = await res.json();
  return {
    sessions: {
      signedInNow: body.sessions.signed_in_now,
      signInsToday: body.sessions.sign_ins_today,
      failedToday: body.sessions.failed_today,
      lockedAccounts: body.sessions.locked_accounts,
    },
    staffByRole: body.staff_by_role,
    portalUsers: body.portal_users,
    deactivatedUsers: body.deactivated_users,
    signInsPerHour: body.sign_ins_per_hour,
    currentHour: body.current_hour,
    recentUsage: body.recent_usage,
    services: heroServices(body.services.map(toHealthService)),
    apiResponseMs: body.api_response_ms,
  };
}
