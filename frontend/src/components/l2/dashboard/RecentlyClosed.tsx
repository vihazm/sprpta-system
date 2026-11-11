import { Card, CardHeading, Chip, LinkButton, muted } from "@/components/dashboard/ui";
import type { ClosedCase } from "./types";

export function RecentlyClosed({ cases, className = "" }: { cases: ClosedCase[]; className?: string }) {
  return (
    <Card className={className}>
      <CardHeading
        title="Recently closed"
        subtitle="Done by staff and approved by you"
        action={<LinkButton>See completed</LinkButton>}
      />
      <ul className="m-0 grid list-none grid-cols-1 gap-3 p-0 sm:grid-cols-2 min-[1200px]:grid-cols-4">
        {cases.map((c) => (
          <li key={c.ref} className="flex min-w-0 flex-col gap-1.5 rounded-[1.25rem] bg-[#f7f4f5] p-4">
            <div className="flex items-center justify-between gap-2">
              <b className="text-[0.78rem] font-extrabold text-crimson-hover">{c.ref}</b>
              <Chip tone="ok">Closed</Chip>
            </div>
            <p className="text-[0.84rem] font-extrabold leading-[1.3]">{c.title}</p>
            <p className={muted}>
              Outcome: {c.outcome} · {c.when}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
