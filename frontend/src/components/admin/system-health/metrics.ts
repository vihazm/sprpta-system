import { formatBytes, formatSince } from "./format";
import { STATE_LABEL, STATE_TONE } from "./status";
import type { ServiceMetric, SystemHealthData } from "./types";

const TREND_POINTS = 24; // the last six hours, in 15 minute steps

/** One tile for each service the backend checks. */
export function buildMetrics(data: SystemHealthData): ServiceMetric[] {
  const { database, apiStartedAt } = data;
  const notes = {
    web: "Reached by the API once a minute.",
    api: `Running since ${formatSince(apiStartedAt)}.`,
    database: `${database.connections} of ${database.maxConnections} connections in use. Size ${formatBytes(database.sizeBytes)}.`,
  };

  return data.services.map((service) => ({
    name: service.name,
    status: STATE_LABEL[service.state],
    tone: STATE_TONE[service.state],
    value: service.latencyMs === null ? "–" : String(service.latencyMs),
    unit: service.latencyMs === null ? "" : "ms",
    note: notes[service.key],
    trend: data.series[service.key].slice(-TREND_POINTS),
  }));
}

// Services that cannot be checked yet, and what each is waiting for.
export const PENDING_SERVICES = [
  { name: "File storage", waitingFor: "Shows free space once documents can be uploaded." },
  { name: "AI service", waitingFor: "Shows answer times once the AI module is connected." },
  { name: "SMS and email", waitingFor: "Shows sent and failed messages once messaging is connected." },
];
