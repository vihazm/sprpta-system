import { api } from "@/lib/api-client";
import type { Tone } from "../dashboard/types";
import type { Backup, FileStorage, HealthService, ServiceKey, ServiceState, SystemHealthData } from "./types";

// The calls behind the System health page. The API speaks snake_case and the
// components camelCase, so the conversion happens here and nowhere else.

const BASE = "/api/admin/system-health";

type ApiService = { key: ServiceKey; name: string; status: ServiceState; latency_ms: number | null };

export function toHealthService(service: ApiService): HealthService {
  return { key: service.key, name: service.name, state: service.status, latencyMs: service.latency_ms };
}

export type ApiFileStorage = {
  total_bytes: number;
  free_bytes: number;
  low: boolean;
  evidence_files: number;
  evidence_bytes: number;
};

export type ApiBackup = {
  finished_at: string;
  succeeded: boolean;
  size_bytes: number | null;
  error: string | null;
  stale: boolean;
};

export function toFileStorage(storage: ApiFileStorage): FileStorage {
  return {
    totalBytes: storage.total_bytes,
    freeBytes: storage.free_bytes,
    low: storage.low,
    evidenceFiles: storage.evidence_files,
    evidenceBytes: storage.evidence_bytes,
  };
}

export function toBackup(backup: ApiBackup | null): Backup | null {
  return (
    backup && {
      finishedAt: backup.finished_at,
      succeeded: backup.succeeded,
      sizeBytes: backup.size_bytes,
      error: backup.error,
      stale: backup.stale,
    }
  );
}

type ApiSystemHealth = {
  checked_at: string | null;
  services: ApiService[];
  series: SystemHealthData["series"];
  uptime: {
    percent: number | null;
    days: SystemHealthData["uptime"]["days"];
    tracking_since: string | null;
    last_outage: {
      service_name: string;
      started_at: string;
      minutes: number | null;
      reason: string | null;
    } | null;
  };
  database: { connections: number; max_connections: number; size_bytes: number; started_at: string };
  api_started_at: string;
  events: { title: string; detail: string | null; occurred_at: string; tone: Tone }[];
  file_storage: ApiFileStorage;
  last_backup: ApiBackup | null;
};

export function toSystemHealth(body: ApiSystemHealth): SystemHealthData {
  const outage = body.uptime.last_outage;
  return {
    checkedAt: body.checked_at,
    services: body.services.map(toHealthService),
    series: body.series,
    uptime: {
      percent: body.uptime.percent,
      days: body.uptime.days,
      trackingSince: body.uptime.tracking_since,
      lastOutage: outage && {
        serviceName: outage.service_name,
        startedAt: outage.started_at,
        minutes: outage.minutes,
        reason: outage.reason,
      },
    },
    database: {
      connections: body.database.connections,
      maxConnections: body.database.max_connections,
      sizeBytes: body.database.size_bytes,
      startedAt: body.database.started_at,
    },
    apiStartedAt: body.api_started_at,
    events: body.events.map((event) => ({
      title: event.title,
      detail: event.detail,
      occurredAt: event.occurred_at,
      tone: event.tone,
    })),
    fileStorage: toFileStorage(body.file_storage),
    lastBackup: toBackup(body.last_backup),
  };
}

/** Asks the backend to check every service now. */
export function runChecks() {
  return api<ApiSystemHealth>(`${BASE}/checks`, { method: "POST" });
}
