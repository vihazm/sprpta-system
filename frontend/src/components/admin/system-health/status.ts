import type { Service, Tone } from "../dashboard/types";
import type { FileStorage, HealthService, ServiceState } from "./types";

export const STATE_TONE: Record<ServiceState, Tone> = {
  ok: "ok",
  slow: "warn",
  down: "crit",
  unknown: "info",
};

export const STATE_LABEL: Record<ServiceState, string> = {
  ok: "Healthy",
  slow: "Slow",
  down: "Down",
  unknown: "Waiting",
};

// Reads as "The API is slow right now." in the hero.
const PROBLEM_PHRASE: Record<Exclude<ServiceState, "ok">, string> = {
  slow: "slow",
  down: "not responding",
  unknown: "still starting up",
};

/** How much of the disk with the evidence files is free, as a whole percent. */
export const percentFree = (storage: FileStorage) => Math.round((100 * storage.freeBytes) / storage.totalBytes);

/** What the hero's ring and pills show: each checked service, then file storage. */
export function heroServices(services: HealthService[], storage: FileStorage): Service[] {
  return [
    ...services.map((service) => ({
      name: service.name,
      tone: STATE_TONE[service.state],
      detail: service.state === "ok" ? `${service.latencyMs} ms` : PROBLEM_PHRASE[service.state],
    })),
    { name: "File storage", tone: storage.low ? "warn" : "ok", detail: `${percentFree(storage)}% free` },
  ];
}
