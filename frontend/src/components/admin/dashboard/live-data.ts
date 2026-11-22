import "server-only";

import { cookies } from "next/headers";
import { ACCESS_COOKIE, API_URL } from "@/lib/auth-constants";
import { statusName } from "../complaint-status";
import { toBackup, toFileStorage, toHealthService } from "../system-health/api";
import { heroServices } from "../system-health/status";
import type { Count, LiveDashboardData } from "./types";

/**
 * The dashboard figures, read for the signed-in administrator. Returns null when
 * the backend cannot be reached or says no.
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
  const fileStorage = toFileStorage(body.file_storage);
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
    services: heroServices(body.services.map(toHealthService), fileStorage),
    apiResponseMs: body.api_response_ms,
    fileStorage,
    lastBackup: toBackup(body.last_backup),
    attention: body.attention,
    areas: body.areas.map((area: { name: string; vehicles: number; has_officer: boolean }) => ({
      name: area.name,
      vehicles: area.vehicles,
      hasOfficer: area.has_officer,
    })),
    masterData: {
      people: body.master_data.people,
      vehicles: body.master_data.vehicles,
      permits: body.master_data.permits,
      routesAndStands: body.master_data.routes_and_stands,
      categories: body.master_data.categories,
      vehiclesWithoutPermit: body.master_data.vehicles_without_permit,
    },
    complaints: {
      perDay: body.complaints.per_day,
      byArea: body.complaints.by_area,
      byStatus: body.complaints.by_status.map((s: Count) => ({ label: statusName(s.label), count: s.count })),
      overdue: body.complaints.overdue,
    },
    timeTargets: body.time_targets.map(
      (t: { severity: string; forward_days: number; decide_days: number; close_days: number }) => ({
        severity: t.severity,
        forwardDays: t.forward_days,
        decideDays: t.decide_days,
        closeDays: t.close_days,
      }),
    ),
  };
}
