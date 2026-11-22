import { api } from "@/lib/api-client";
import type { EntityKey, Row } from "./entities";

// The calls behind the master data screens. Rows keep the API's snake_case names: the table and the form are
// driven by field keys (see entities.ts), so converting them would only add a second set of names.

const BASE = "/api/admin/master-data";

export type EntityCount = { key: EntityKey; total: number; active: number };

export type Status = "active" | "inactive" | null;

export type RecordPage = {
  items: Row[];
  total: number;
  page: number;
  page_size: number;
  counts: { all: number; active: number; inactive: number };
};

export function loadCounts() {
  return api<EntityCount[]>(BASE);
}

export function loadRecords(
  entity: EntityKey,
  query: { search?: string; status?: Status; page?: number; pageSize?: number } = {},
) {
  const params = new URLSearchParams({ page: String(query.page ?? 1) });
  if (query.search) params.set("search", query.search);
  if (query.status) params.set("status", query.status);
  if (query.pageSize) params.set("page_size", String(query.pageSize));
  return api<RecordPage>(`${BASE}/${entity}?${params}`);
}

export type Values = Record<string, string | number | null>;

/** Adds a record when `id` is null, otherwise saves the changes to it. */
export function saveRecord(entity: EntityKey, id: number | null, values: Values, active: boolean) {
  return id === null
    ? api<Row>(`${BASE}/${entity}`, { method: "POST", body: { values } })
    : api<Row>(`${BASE}/${entity}/${id}`, { method: "PUT", body: { values, is_active: active } });
}
