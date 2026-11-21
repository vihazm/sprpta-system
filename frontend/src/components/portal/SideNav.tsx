"use client";

import Link, { useLinkStatus } from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";
import type { NavItem } from "@/lib/roles";

/** Sits inside a link and marks it while its page is loading, so the link can show it was pressed. */
function Pending() {
  const { pending } = useLinkStatus();
  return <span hidden data-pending={pending ? "" : undefined} />;
}

/**
 * Sits inside a link and marks it when the page being shown is that item's page, or one under it (a case under
 * Cases). The address is only known when the page is requested, so this waits in its own Suspense: the menu is on
 * screen at once and the current item is marked a moment later.
 */
function Current({ href }: { href: string }) {
  const pathname = usePathname();
  const current = pathname === href || pathname.startsWith(`${href}/`);
  return current ? <span data-current className="sr-only">(current page)</span> : null;
}

/** Side navigation: only the items of the signed-in role (UI Flow 1.3). */
export function SideNav({ items }: { items: NavItem[] }) {
  return (
    <nav
      aria-label="Main"
      className="flex flex-none flex-row flex-wrap gap-[0.3rem] rounded-[1.4rem] bg-white p-[0.7rem] shadow-[0_0_0_1px_rgba(60,20,30,0.05)] min-[900px]:w-[15.5rem] min-[900px]:flex-col min-[900px]:self-start"
    >
      {items.map((item) =>
        item.href ? (
          <Link
            key={item.label}
            href={item.href}
            // Pressed or current: crimson. Pressed shows at once while the mouse is down and until the page has loaded.
            className="focus-ring rounded-[0.9rem] px-[0.95rem] py-[0.65rem] text-[0.92rem] font-bold text-slate-ink transition-colors duration-100 hover:bg-field active:bg-crimson active:text-white has-[[data-current]]:bg-crimson has-[[data-current]]:text-white has-[[data-pending]]:bg-crimson has-[[data-pending]]:text-white"
          >
            {item.label}
            <Pending />
            <Suspense fallback={null}>
              <Current href={item.href} />
            </Suspense>
          </Link>
        ) : (
          <span
            key={item.label}
            aria-disabled="true"
            className="flex items-center justify-between gap-2 rounded-[0.9rem] px-[0.95rem] py-[0.65rem] text-[0.92rem] font-semibold text-[#9AA0AA]"
          >
            {item.label}
            <span className="rounded-full bg-field px-[0.5rem] py-[0.1rem] text-[0.66rem] font-bold uppercase tracking-[0.04em] text-muted">
              Soon
            </span>
          </span>
        ),
      )}
    </nav>
  );
}
