import { Card, CardHeading, Chip, StatusDot, muted, type Tone } from "@/components/dashboard/ui";
import { formatBytes, formatSince } from "./format";
import type { Backup } from "./types";

/** How the last backup went, in a word and a tone. */
function backupState(backup: Backup | null): { label: string; tone: Tone } {
  if (!backup) return { label: "Not set up", tone: "info" };
  if (!backup.succeeded) return { label: "Failed", tone: "crit" };
  return backup.stale ? { label: "Missed", tone: "warn" } : { label: "Up to date", tone: "ok" };
}

const TINT: Partial<Record<Tone, string>> = { warn: "!bg-amber-50", crit: "!bg-red-50" };

// The daily backup (F-66). The backup script records each run; this shows the last one.
export function BackupTile({ backup, className = "" }: { backup: Backup | null; className?: string }) {
  const state = backupState(backup);

  return (
    <Card className={`${TINT[state.tone] ?? ""} ${className}`}>
      <CardHeading
        title="Backups"
        action={
          <Chip tone={state.tone}>
            <StatusDot tone={state.tone} />
            {state.label}
          </Chip>
        }
      />
      {backup ? (
        <>
          <p className="font-display text-[1.6rem] leading-[1.1] tracking-[-0.03em]">
            {backup.succeeded ? "Last backup" : "Last attempt"} {formatSince(backup.finishedAt)}
          </p>
          <p className={muted}>
            {backup.succeeded
              ? `The database and the evidence files, ${formatBytes(backup.sizeBytes ?? 0)}.`
              : backup.error}
            {backup.stale && " The daily backup has not run since."}
          </p>
        </>
      ) : (
        <p className={muted}>
          No backup has been made yet. Schedule the backup script to run once a day, as the README describes.
        </p>
      )}
    </Card>
  );
}
