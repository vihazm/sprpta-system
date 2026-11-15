"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Icon } from "@/components/dashboard/icons";
import { notify } from "@/lib/notify";
import { findReference } from "./api";

// "Find reference no." in the dashboard banner. A draft or an incomplete case opens in the form so it can be
// finished; one that has left Level 1 cannot be changed, so its status and where it went are shown instead.
export function ReferenceFinder() {
  const router = useRouter();
  const [reference, setReference] = useState("");
  const [busy, setBusy] = useState(false);

  async function find(event: FormEvent) {
    event.preventDefault();
    const wanted = reference.trim();
    if (!wanted || busy) return;
    setBusy(true);
    const result = await findReference(wanted);
    setBusy(false);
    if (!result.ok) return notify.error("Not found", result.message);

    const hit = result.data;
    if (hit.editable) {
      notify.success(`${hit.reference} · ${hit.status}`, "Opening it so you can finish it.");
      router.push(`/l1/new-complaint?id=${hit.id}`);
    } else {
      const where = hit.forwardedTo ? `With the ${hit.area} area officer, ${hit.forwardedTo}.` : "It can no longer be changed.";
      notify.success(`${hit.reference} · ${hit.status}`, `${hit.subject ?? "No subject"}. ${where}`);
    }
    setReference("");
  }

  return (
    <form onSubmit={find} className="flex h-[2.6rem] items-center gap-2 rounded-full border border-white/30 bg-white/15 px-4 text-white/90">
      <Icon name="search" size={15} />
      <label className="sr-only" htmlFor="find-reference">
        Find a case by reference number
      </label>
      <input
        id="find-reference"
        type="search"
        value={reference}
        onChange={(e) => setReference(e.target.value)}
        placeholder="Find reference no."
        autoComplete="off"
        disabled={busy}
        className="w-[8.5rem] bg-transparent text-[0.8rem] text-white outline-none placeholder:text-white/80"
      />
    </form>
  );
}