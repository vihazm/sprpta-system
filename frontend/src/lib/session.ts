import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ACCESS_COOKIE, API_URL } from "@/lib/auth-constants";
import { LANDING_PATH, isRole, type Role } from "@/lib/roles";

export type SessionUser = {
  id: number;
  name: string;
  role: Role;
  areaId: number | null;
  areaName: string | null;
  kind: "staff" | "cp";
};

/**
 * The signed-in user, asked of the backend on every request (never cached
 * across requests, so logout and deactivation apply at once). React's cache()
 * only de-duplicates calls within the same render.
 *
 * Call it inside a <Suspense> boundary: it reads cookies, which Cache
 * Components treats as request-time data.
 */
export const getSession = cache(async (): Promise<SessionUser | null> => {
  const jar = await cookies();
  const access = jar.get(ACCESS_COOKIE)?.value;
  if (!access) return null;

  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/auth/me`, {
      headers: { cookie: `${ACCESS_COOKIE}=${access}` },
      cache: "no-store",
    });
  } catch {
    return null; // backend unreachable: treat as signed out rather than crash
  }
  if (!res.ok) return null;

  const body = await res.json();
  if (!isRole(body?.user?.role)) return null;
  return {
    id: body.user.id,
    name: body.user.name,
    role: body.user.role,
    areaId: body.user.area_id ?? null,
    areaName: body.user.area_name ?? null,
    kind: body.user.kind,
  };
});

/** Guard for a role's pages: signed in, and of the right role. */
export async function requireRole(role: Role): Promise<SessionUser> {
  const session = await getSession();
  if (!session) redirect("/?reason=expired");
  if (session.role !== role) redirect(`${LANDING_PATH[session.role]}?denied=1`);
  return session;
}
