import type { ReactNode } from "react";
import { BrandTile } from "@/components/BrandTile";
import { NAV_ITEMS, ROLE_LABEL, type Role } from "@/lib/roles";
import { requireRole } from "@/lib/session";
import { AuthSync } from "./AuthSync";
import { LogoutButton } from "./LogoutButton";
import { SideNav } from "./SideNav";

/**
 * The signed-in frame (UI Flow 1.2): header with name, role and Log out, plus
 * the side navigation of this role. It re-checks the session with the backend
 * on every request and sends the user away if they are not allowed in.
 */
export async function PortalShell({
  role,
  children,
}: {
  role: Role;
  children: ReactNode;
}) {
  const user = await requireRole(role);

  return (
    <div className="flex min-h-dvh flex-col bg-page">
      <AuthSync />
      <header className="flex items-center justify-between gap-4 bg-white px-[1.6rem] py-[0.75rem] shadow-[0_1px_0_rgba(60,20,30,0.06)] max-[899px]:px-[1rem]">
        <div className="flex items-center gap-[0.7rem]">
          <BrandTile size="2.3rem" />
          <span className="text-[1.05rem] font-extrabold tracking-[0.04em] text-slate-ink">
            SPRPTA
          </span>
        </div>
        <div className="flex items-center gap-[1rem]">
          <div className="text-right leading-[1.25] max-[599px]:hidden">
            <p className="m-0 text-[0.92rem] font-bold text-ink">{user.name}</p>
            <p className="m-0 text-[0.78rem] font-medium text-muted">
              {ROLE_LABEL[user.role]}
              {user.areaName ? ` · ${user.areaName}` : ""}
            </p>
          </div>
          <LogoutButton />
        </div>
      </header>

      <div className="flex flex-1 flex-col gap-[1rem] p-[1.2rem] min-[900px]:flex-row min-[900px]:gap-[1.4rem] min-[900px]:px-[1.6rem]">
        <SideNav items={NAV_ITEMS[role]} />
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
