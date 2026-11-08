import { ROLE_LABEL } from "@/lib/roles";
import { getSession } from "@/lib/session";

/**
 * Placeholder body for every role's landing page, until the real screens are
 * built. Shows a welcome message so sign-in and redirects can be checked.
 */
export async function WelcomePanel({ screen }: { screen: string }) {
  const user = await getSession();
  if (!user) return null; // the shell has already redirected unauthenticated visitors

  return (
    <div className="flex flex-col gap-[1rem]">
      <section className="rounded-[1.6rem] bg-white px-[2rem] py-[1.8rem] shadow-[0_1px_2px_rgba(60,20,30,0.05),0_24px_48px_-30px_rgba(110,8,30,0.28),0_0_0_1px_rgba(60,20,30,0.04)]">
        <p className="m-0 text-[0.8rem] font-bold uppercase tracking-[0.08em] text-crimson">
          {screen}
        </p>
        <h1 className="mb-0 mt-[0.4rem] text-[2rem] font-extrabold leading-[1.15] tracking-[-0.03em] text-ink">
          Welcome, {user.name}
        </h1>
        <p className="mb-0 mt-[0.5rem] text-[1rem] text-muted">
          You are signed in as {ROLE_LABEL[user.role]}
          {user.areaName ? ` for ${user.areaName}` : ""}.
        </p>
      </section>
      <section className="rounded-[1.6rem] border-[1.5px] border-dashed border-[#E2D6DA] px-[2rem] py-[2.4rem] text-center">
        <p className="m-0 text-[0.95rem] font-semibold text-slate-ink">
          This page is blank for now.
        </p>
        <p className="mb-0 mt-[0.3rem] text-[0.86rem] text-muted">
          The screens for your role will appear here as they are built.
        </p>
      </section>
    </div>
  );
}
