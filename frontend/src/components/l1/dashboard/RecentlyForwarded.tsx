import { SeverityChip } from "@/components/dashboard/severity";
import { Card, CardHeading, LinkButton, muted } from "@/components/dashboard/ui";
import type { ForwardedCase } from "./types";

// A failed message never blocks a case, so it is only noted here.
const MESSAGE = {
  sent: { text: "Registration message sent", dot: "bg-emerald-500" },
  none: { text: "No contact, no message sent", dot: "bg-slate-400" },
  failed: { text: "Message failed, case not blocked", dot: "bg-orange-500" },
};

export function RecentlyForwarded({ cases, className = "" }: { cases: ForwardedCase[]; className?: string }) {
  return (
    <Card className={className}>
      <CardHeading
        title="Recently forwarded"
        subtitle="Your latest complaints sent to Level 2. Complainants with a contact on record receive a registration message with the reference number."
        action={<LinkButton>See all</LinkButton>}
      />
      <ul className="m-0 grid list-none grid-cols-1 gap-3 p-0 sm:grid-cols-2 min-[1200px]:grid-cols-4">
        {cases.map((c) => (
          <li key={c.ref} className="flex min-w-0 flex-col gap-1.5 rounded-[1.25rem] bg-[#f7f4f5] p-4">
            <div className="flex items-center justify-between gap-2">
              <b className="text-[0.78rem] font-extrabold text-crimson-hover">{c.ref}</b>
              <SeverityChip severity={c.severity} />
            </div>
            <p className="text-[0.84rem] font-extrabold leading-[1.3]">{c.title}</p>
            <p className={muted}>
              To {c.area} officer · {c.when}
            </p>
            <p className={`${muted} flex items-center gap-1.5`}>
              <span aria-hidden="true" className={`size-[0.45rem] rounded-full ${MESSAGE[c.message].dot}`} />
              {MESSAGE[c.message].text}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
