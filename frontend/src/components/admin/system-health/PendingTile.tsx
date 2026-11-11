import { Card, CardHeading, Chip, muted } from "@/components/dashboard/ui";

// A service that cannot be checked yet. It says so, instead of showing made-up numbers.
export function PendingTile({
  name,
  waitingFor,
  className = "",
}: {
  name: string;
  waitingFor: string;
  className?: string;
}) {
  return (
    <Card
      className={`border-[1.5px] border-dashed border-[#E2D6DA] !bg-transparent !shadow-none ${className}`}
    >
      <CardHeading title={name} action={<Chip>Not set up</Chip>} />
      <p className={muted}>{waitingFor}</p>
    </Card>
  );
}
