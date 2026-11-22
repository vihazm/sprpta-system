import { Card, CardHeading, Chip, StatusDot, bigNumber, muted } from "@/components/dashboard/ui";
import { formatBytes } from "./format";
import { percentFree } from "./status";
import type { FileStorage } from "./types";

// The disk that holds the evidence files: how much of it is free, and how much the evidence takes up.
export function FileStorageTile({ storage, className = "" }: { storage: FileStorage; className?: string }) {
  const free = percentFree(storage);
  const tone = storage.low ? "warn" : "ok";

  return (
    <Card className={`${storage.low ? "!bg-amber-50" : ""} ${className}`}>
      <CardHeading
        title="File storage"
        action={
          <Chip tone={tone}>
            <StatusDot tone={tone} />
            {storage.low ? "Low on space" : "Healthy"}
          </Chip>
        }
      />
      <p className={`${bigNumber} text-[2.75rem]`}>
        {free}
        <span className="ml-1.5 text-[1.1rem] font-bold text-muted">% free</span>
      </p>
      <div
        role="img"
        aria-label={`${100 - free}% of the disk is in use`}
        className="h-2.5 overflow-hidden rounded-full bg-[#ece4e7]"
      >
        <div
          className={`h-full rounded-full ${storage.low ? "bg-amber-500" : "bg-emerald-500"}`}
          style={{ width: `${100 - free}%` }}
        />
      </div>
      <p className={muted}>
        {formatBytes(storage.freeBytes)} free of {formatBytes(storage.totalBytes)}. Evidence:{" "}
        {storage.evidenceFiles} {storage.evidenceFiles === 1 ? "file" : "files"}, {formatBytes(storage.evidenceBytes)}.
      </p>
    </Card>
  );
}
