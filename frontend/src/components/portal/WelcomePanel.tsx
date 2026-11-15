import { Suspense, type ReactNode } from "react";
import { ROLE_LABEL } from "@/lib/roles";
import { getSession } from "@/lib/session";
import { Skeleton } from "./Skeleton";

/**
 * The welcome card at the top of every role's landing page. Below it goes the
 * page's content; until a role's screens are built, a placeholder shows instead.
 * The card is on screen at once; only the name waits for the session.
 */
export function WelcomePanel({
  screen,
  children,
}: {
  screen: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-[1rem]">
      <section className="rounded-[1.6rem] bg-white px-[2rem] py-[1.8rem] shadow-[0_1px_2px_rgba(60,20,30,0.05),0_24px_48px_-30px_rgba(110,8,30,0.28),0_0_0_1px_rgba(60,20,30,0.04)]">
        <p className="m-0 text-[0.8rem] font-bold uppercase tracking-[0.08em] text-crimson">
          {screen}
        </p>
        <Suspense fallback={<WelcomeSkeleton />}>
          <Welcome />
        </Suspense>
      </section>
      {children ?? (
        <section className="rounded-[1.6rem] border-[1.5px] border-dashed border-[#E2D6DA] px-[2rem] py-[2.4rem] text-center">
          <p className="m-0 text-[0.95rem] font-semibold text-slate-ink">
            This page is blank for now.
          </p>
          <p className="mb-0 mt-[0.3rem] text-[0.86rem] text-muted">
            The screens for your role will appear here as they are built.
          </p>
        </section>
      )}
    </div>
  );
}

async function Welcome() {
  const user = await getSession();
  if (!user) return null; // the shell has already redirected unauthenticated visitors

  return (
    <>
      <h1 className="mb-0 mt-[0.4rem] text-[2rem] font-extrabold leading-[1.15] tracking-[-0.03em] text-ink">
        Welcome, {user.name}
      </h1>
      <p className="mb-0 mt-[0.5rem] text-[1rem] text-muted">
        You are signed in as {ROLE_LABEL[user.role]}
        {user.areaName ? ` for ${user.areaName}` : ""}.
      </p>
    </>
  );
}

// The same height as the two lines above, so nothing moves when the name arrives.
function WelcomeSkeleton() {
  return (
    <>
      <div className="mb-0 mt-[0.4rem] flex h-[2.3rem] items-center">
        <Skeleton className="h-[1.5rem] w-72 max-w-full" />
      </div>
      <div className="mb-0 mt-[0.5rem] flex h-[1.5rem] items-center">
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
    </>
  );
}
