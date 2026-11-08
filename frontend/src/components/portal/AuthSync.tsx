"use client";

import { useEffect } from "react";
import { AUTH_CHANNEL } from "@/lib/auth-client";

/** When the user logs out in one tab, send every other open tab to the login page. */
export function AuthSync() {
  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;
    const channel = new BroadcastChannel(AUTH_CHANNEL);
    channel.onmessage = (event) => {
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- full page load on purpose
      if (event.data === "logout") window.location.assign("/?reason=signed-out");
    };
    return () => channel.close();
  }, []);
  return null;
}
