import { bigNumber } from "@/components/dashboard/ui";

type Sessions = {
  signedInNow: number;
  signInsToday: number;
  failedToday: number;
  lockedAccounts: number;
};

function Row({ label, value, alert = false }: { label: string; value: number; alert?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[0.8rem] text-white/80">{label}</span>
      <span className={`font-display text-[1.4rem] ${alert ? "text-[#ffb4ab]" : ""}`}>{value}</span>
    </div>
  );
}

export function SignedInNow({ sessions, className = "" }: { sessions: Sessions; className?: string }) {
  return (
    <section
      className={`flex min-w-0 flex-col justify-between gap-5 rounded-[1.75rem] bg-slate-ink p-6 text-white shadow-[0_26px_50px_-34px_rgba(20,28,40,0.7)] ${className}`}
    >
      <div>
        <p className="text-[0.69rem] font-bold uppercase tracking-[0.09em] text-white/65">
          Signed in now
        </p>
        <p className={`${bigNumber} mt-2 text-[5.25rem] leading-[0.95]`}>{sessions.signedInNow}</p>
      </div>
      <div className="flex flex-col gap-[0.6rem]">
        <div className="border-t border-white/15 pt-3">
          <Row label="Sign-ins in 24 hours" value={sessions.signInsToday} />
        </div>
        <Row label="Failed sign-ins" value={sessions.failedToday} alert />
        <Row label="Locked accounts" value={sessions.lockedAccounts} alert />
      </div>
    </section>
  );
}
