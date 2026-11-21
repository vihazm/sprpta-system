import { Card, PillLink, muted } from "@/components/dashboard/ui";

// A case or recommendation that does not exist, or that is not in this officer's area, inside the portal frame.
export default function NotFound() {
  return (
    <Card className="max-w-[40rem]">
      <p className="text-[0.69rem] font-extrabold uppercase tracking-[0.09em] text-crimson">Not found</p>
      <h2 className="font-display text-[1.6rem] leading-[1.15] tracking-[-0.035em]">We could not find that page</h2>
      <p className={muted}>
        The case or recommendation does not exist, or it belongs to another area. Check the reference number and try
        again from the list.
      </p>
      <div className="flex flex-wrap gap-2">
        <PillLink primary href="/l2/cases">
          Back to cases
        </PillLink>
        <PillLink href="/l2/dashboard">Dashboard</PillLink>
      </div>
    </Card>
  );
}
