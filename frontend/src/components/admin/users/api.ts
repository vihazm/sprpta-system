import { api, type ApiResult } from "@/lib/api-client";
import type { StatusFilter } from "./staff";
import type { StaffRole, StaffUser, UserForm, UserPage, UsersSummary } from "./types";

// The calls behind the Users page. The API speaks snake_case and the components
// camelCase, so the conversion happens here and nowhere else.

const BASE = "/api/admin/users";

type ApiUser = {
  id: number;
  full_name: string;
  login: string;
  role: StaffRole;
  area_id: number | null;
  area_name: string | null;
  status: StaffUser["status"];
  signed_in: boolean;
  last_login_at: string | null;
  created_at: string;
};

function toUser(user: ApiUser): StaffUser {
  return {
    id: user.id,
    name: user.full_name,
    login: user.login,
    role: user.role,
    areaId: user.area_id,
    area: user.area_name,
    status: user.status,
    signedIn: user.signed_in,
    lastSignIn: user.last_login_at,
    created: user.created_at,
  };
}

/** Used by the server when it reads the summary for the first page load. */
export function toSummary(body: {
  active: number;
  signed_in_now: number;
  locked: number;
  inactive: number;
  by_role: UsersSummary["byRole"];
  areas: { id: number; name: string; officer_id: number | null; officer_name: string | null }[];
}): UsersSummary {
  return {
    active: body.active,
    signedInNow: body.signed_in_now,
    locked: body.locked,
    inactive: body.inactive,
    byRole: body.by_role,
    areas: body.areas.map((a) => ({
      id: a.id,
      name: a.name,
      officerId: a.officer_id,
      officerName: a.officer_name,
    })),
  };
}

function mapData<A, B>(result: ApiResult<A>, convert: (data: A) => B): ApiResult<B> {
  return result.ok ? { ok: true, data: convert(result.data) } : result;
}

export async function loadUsers(filters: {
  search: string;
  status: StatusFilter;
  role: StaffRole | "all";
  page: number;
}): Promise<ApiResult<UserPage>> {
  const params = new URLSearchParams({ page: String(filters.page) });
  if (filters.search) params.set("search", filters.search);
  if (filters.status) params.set("status", filters.status);
  if (filters.role !== "all") params.set("role", filters.role);

  const result = await api<{
    items: ApiUser[];
    page: number;
    total: number;
    page_size: number;
    role_counts: UserPage["roleCounts"];
  }>(`${BASE}?${params}`);
  return mapData(result, (body) => ({
    users: body.items.map(toUser),
    page: body.page,
    total: body.total,
    pageSize: body.page_size,
    roleCounts: body.role_counts,
  }));
}

function fields(form: UserForm) {
  return { full_name: form.name, login: form.login, role: form.role, area_id: form.areaId };
}

export async function createUser(form: UserForm, password: string) {
  const result = await api<ApiUser>(BASE, { method: "POST", body: { ...fields(form), password } });
  return mapData(result, toUser);
}

export async function updateUser(id: number, form: UserForm) {
  const result = await api<ApiUser>(`${BASE}/${id}`, {
    method: "PUT",
    body: { ...fields(form), is_active: form.active },
  });
  return mapData(result, toUser);
}

export async function unlockUser(id: number) {
  const result = await api<ApiUser>(`${BASE}/${id}/unlock`, { method: "POST" });
  return mapData(result, toUser);
}
