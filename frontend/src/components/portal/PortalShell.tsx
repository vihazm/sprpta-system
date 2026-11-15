import { Suspense, type ReactNode } from "react";
import { BrandTile } from "@/components/BrandTile";
import { NAV_ITEMS, ROLE_LABEL, type Role } from "@/lib/roles";
import { requireRole } from "@/lib/session";
import { AuthSync } from "./AuthSync";
import { LogoutButton } from "./LogoutButton";
import { Skeleton } from "./Skeleton";
import { SideNav } from "./SideNav";

/**
 * The signed-in frame (UI Flow 1.2): header with name, role and Log out, plus the side navigation of this role.
 * Use it in a role's layout.tsx.
 *
 * The frame itself needs nothing from the backend, so it is on screen at once and stays put while the page
 * beside it changes. Only the user's name waits for the session, which is checked with the backend on every
 * request; a user who is not allowed in is sent away from there. (Next.js Cache Components: anything that reads
 * the session must sit behind a Suspense boundary.)
 */
export function PortalShell({ role, children }: { role: Role; children: ReactNode }) {
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
          <Suspense fallback={<UserSkeleton />}>
            <SignedInUser role={role} />
          </Suspense>
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

async function SignedInUser({ role }: { role: Role }) {
  const user = await requireRole(role);
  return (
    <div className="text-right leading-[1.25] max-[599px]:hidden">
      <p className="m-0 text-[0.92rem] font-bold text-ink">{user.name}</p>
      <p className="m-0 text-[0.78rem] font-medium text-muted">
        {ROLE_LABEL[user.role]}
        {user.areaName ? ` · ${user.areaName}` : ""}
      </p>
    </div>
  );
}

function UserSkeleton() {
  return (
    <div className="flex flex-col items-end gap-1.5 max-[599px]:hidden">
      <Skeleton className="h-3.5 w-28" />
      <Skeleton className="h-3 w-36" />
    </div>
  );
}
