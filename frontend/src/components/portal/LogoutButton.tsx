"use client";

import { useState } from "react";
import { signOut } from "@/lib/auth-client";

export function LogoutButton() {
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      disabled={busy}
      onClick={() => {
        setBusy(true);
        void signOut();
      }}
      className="focus-ring h-[2.5rem] cursor-pointer rounded-[0.8rem] border-[1.5px] border-[#E5E7EB] bg-white px-[1rem] text-[0.86rem] font-bold text-slate-ink transition-colors hover:border-crimson hover:text-crimson disabled:cursor-wait disabled:opacity-60"
    >
      {busy ? "Logging out…" : "Log out"}
    </button>
  );
}
