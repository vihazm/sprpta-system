import { Suspense, type ReactNode } from "react";
import { BrandTile } from "@/components/BrandTile";
import { AuthSync } from "@/components/portal/AuthSync";
import { LogoutButton } from "@/components/portal/LogoutButton";
import { Skeleton } from "@/components/portal/Skeleton";
import { ROLE_LABEL } from "@/lib/roles";
import { requireRole } from "@/lib/session";
import { CpNav } from "./CpNav";

/**
 * The signed-in frame of the complainant portal: a crimson side panel with the navigation, the person's name
 * and Log out. Like the shell of the other roles it is on screen at once; only the name waits for the session,
 * which is checked with the backend on every request.
 */
export function ComplainantShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh gap-[1.4rem] bg-page p-[1.2rem] max-[899px]:flex-col max-[899px]:gap-[1rem] max-[899px]:p-[0.8rem]">
      <AuthSync />
      <aside className="flex w-[16.5rem] flex-none flex-col gap-[0.4rem] rounded-[1.75rem] bg-gradient-to-b from-crimson-deep via-[#8d0c27] to-[#a8102f] p-[1.1rem] text-white shadow-[0_34px_60px_-36px_rgba(110,8,30,0.75)] max-[899px]:w-auto min-[900px]:sticky min-[900px]:top-[1.2rem] min-[900px]:h-[calc(100dvh-2.4rem)]">
        <div className="flex items-center gap-[0.7rem] px-[0.4rem] pb-[1.2rem] pt-[0.3rem]">
          <span className="flex size-[2.4rem] flex-none items-center justify-center rounded-[0.8rem] bg-white">
            <BrandTile size="1.7rem" />
          </span>
          <span className="text-[1.05rem] font-extrabold tracking-[0.04em]">SPRPTA</span>
        </div>
        <CpNav />
        <div className="mt-auto flex flex-col gap-[0.8rem] border-t border-white/15 px-[0.4rem] pt-[1rem] max-[899px]:mt-[0.6rem]">
          <Suspense fallback={<UserSkeleton />}>
            <SignedInUser />
          </Suspense>
          <LogoutButton />
        </div>
      </aside>
      <main className="min-w-0 flex-1 pt-[0.2rem]">{children}</main>
    </div>
  );
}

async function SignedInUser() {
  const user = await requireRole("cp");
  return (
    <div className="leading-[1.3]">
      <p className="m-0 text-[0.92rem] font-bold">{user.name}</p>
      <p className="m-0 text-[0.78rem] text-white/75">{ROLE_LABEL[user.role]}</p>
    </div>
  );
}

function UserSkeleton() {
  return (
    <div className="flex flex-col gap-1.5">
      <Skeleton className="h-3.5 w-28 !bg-white/20" />
      <Skeleton className="h-3 w-20 !bg-white/15" />
    </div>
  );
}
