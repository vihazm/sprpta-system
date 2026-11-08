"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { NavItem } from "@/lib/roles";

/** Side navigation: only the items of the signed-in role (UI Flow 1.3). */
export function SideNav({ items }: { items: NavItem[] }) {
  const pathname = usePathname();
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
            aria-current={pathname === item.href ? "page" : undefined}
            className={`focus-ring rounded-[0.9rem] px-[0.95rem] py-[0.65rem] text-[0.92rem] font-bold transition-colors ${
              pathname === item.href
                ? "bg-crimson text-white"
                : "text-slate-ink hover:bg-field"
            }`}
          >
            {item.label}
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
