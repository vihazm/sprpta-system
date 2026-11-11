"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { notify } from "@/lib/notify";
import { PillButton } from "@/components/dashboard/ui";
import { runChecks } from "./api";

export function RunChecksButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    const result = await runChecks();
    setBusy(false);

    if (!result.ok) return notify.error("Could not run the checks", result.message);
    notify.success("Checks finished", "Every service was checked just now.");
    router.refresh();
  }

  return (
    <PillButton primary onClick={run} disabled={busy}>
      {busy ? "Checking…" : "Run all checks now"}
    </PillButton>
  );
}
