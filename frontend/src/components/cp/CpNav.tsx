"use client";

import Link, { useLinkStatus } from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { NAV_ITEMS } from "@/lib/roles";

const ICONS: Record<string, ReactNode> = {
  "/cp/dashboard": (
    <>
      <rect x="3.5" y="3.5" width="7" height="7" rx="2" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="2" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="2" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="2" />
    </>
  ),
  "/cp/new-complaint": (
    <>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5M12 11.5v6M9 14.5h6" />
    </>
  ),
  "/cp/complaints": (
    <>
      <path d="M4 6h16M4 12h16M4 18h10" />
      <circle cx="19" cy="18" r="1.6" />
    </>
  ),
};

/** Shows the pressed look at once while the next page loads, like the side navigation of the other roles. */
function Pending() {
  const { pending } = useLinkStatus();
  return <span hidden data-pending={pending ? "" : undefined} />;
}

/** The complainant's side navigation: Dashboard, New complaint, My complaints. */
export function CpNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="flex flex-col gap-[0.35rem] max-[899px]:flex-row max-[899px]:flex-wrap">
      {NAV_ITEMS.cp.map((item) => {
        if (!item.href) return null;
        const current = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={current ? "page" : undefined}
            className="focus-ring flex items-center gap-[0.7rem] rounded-[0.95rem] px-[0.95rem] py-[0.7rem] text-[0.92rem] font-bold text-white/90 transition-colors duration-100 hover:bg-white/15 hover:text-white aria-[current=page]:bg-white aria-[current=page]:text-crimson has-[[data-pending]]:bg-white has-[[data-pending]]:text-crimson max-[899px]:flex-1 max-[899px]:justify-center"
          >
            <svg
              width="19"
              height="19"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.9"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              className="flex-none"
            >
              {ICONS[item.href]}
            </svg>
            {item.label}
            <Pending />
          </Link>
        );
      })}
    </nav>
  );
}
