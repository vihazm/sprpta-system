"use client";

import { Suspense, useSyncExternalStore } from "react";
import { getSnapshot, remove, subscribe } from "@/lib/notify";
import { IslandPill } from "./IslandPill";
import { UrlNotices } from "./UrlNotices";

/** Mounted once in the root layout. Draws whatever notify.success/error asked for. */
export function Toaster() {
  const toast = useSyncExternalStore(subscribe, getSnapshot, () => null);
  return (
    <>
      {toast && <IslandPill key={toast.id} toast={toast} onRemove={remove} />}
      <Suspense>
        <UrlNotices />
      </Suspense>
    </>
  );
}
