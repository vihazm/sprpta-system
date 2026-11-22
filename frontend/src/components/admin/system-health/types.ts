import type { Tone } from "../dashboard/types";

// Shapes used by the administrator's System health page (UI-AD-07).
// The web app, the API and the database are timed; file storage and backups are read as they are.

export type ServiceKey = "web" | "api" | "database";

// "unknown" means there is no recent reading, for example right after the first start.
export type ServiceState = "ok" | "slow" | "down" | "unknown";

export type HealthService = {
  key: ServiceKey;
  name: string;
  state: ServiceState;
  latencyMs: number | null;
};

type Outage = {
  serviceName: string;
  startedAt: string;
  minutes: number | null; // null while it is still going on
  reason: string | null;
};

export type Uptime = {
  percent: number | null; // null until the first reading
  days: ("up" | "down" | "unknown")[]; // the last 30 days, oldest first
  trackingSince: string | null;
  lastOutage: Outage | null;
};

export type HealthEvent = {
  title: string;
  detail: string | null;
  occurredAt: string;
  tone: Tone;
};

export type FileStorage = {
  totalBytes: number; // the disk the evidence folder is on
  freeBytes: number;
  low: boolean; // less than a tenth of the disk is free
  evidenceFiles: number;
  evidenceBytes: number;
};

/** The last run of the backup script. */
export type Backup = {
  finishedAt: string;
  succeeded: boolean;
  sizeBytes: number | null;
  error: string | null;
  stale: boolean; // more than a day old, so the daily run was missed
};

export type SystemHealthData = {
  checkedAt: string | null; // when the newest reading was taken
  services: HealthService[];
  series: Record<ServiceKey, number[]>; // response times in 15 minute steps over 24 hours
  uptime: Uptime;
  database: { connections: number; maxConnections: number; sizeBytes: number; startedAt: string };
  apiStartedAt: string;
  events: HealthEvent[];
  fileStorage: FileStorage;
  lastBackup: Backup | null; // null until the backup script has run once
};

// What one service tile shows.
export type ServiceMetric = {
  name: string;
  status: string;
  tone: Tone;
  value: string;
  unit: string;
  note: string;
  trend: number[];
};
