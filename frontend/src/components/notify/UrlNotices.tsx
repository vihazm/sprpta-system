"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";
import { notify } from "@/lib/notify";

/**
 * Turns "why am I here" hints in the address bar into a notification, then
 * removes them from the address:
 *   /?reason=signed-out   after logging out
 *   /?reason=expired      the session ended (timeout, logout elsewhere, deactivation)
 *   ?denied=1             tried to open another role's page
 * Used for full page loads, where an in-memory notify() call would be lost.
 */
export function UrlNotices() {
  const params = useSearchParams();
  const handled = useRef("");

  useEffect(() => {
    const reason = params.get("reason");
    const denied = params.get("denied");
    const key = `${reason}|${denied}`;
    if ((!reason && !denied) || handled.current === key) return;
    handled.current = key;

    if (reason === "signed-out") notify.success("Signed out", "You have been signed out.");
    else if (reason === "expired") notify.error("Session ended", "Please sign in again.");
    else if (denied === "1")
      notify.error("No access", "You do not have access to that page. Here is your own area instead.");

    const url = new URL(window.location.href);
    url.searchParams.delete("reason");
    url.searchParams.delete("denied");
    window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
  }, [params]);

  return null;
}
