import { BarRows, type BarItem } from "./BarRows";
import { Note } from "./Note";
import { Card, CardHeading } from "./ui";

// A card that ranks a few things with bars and ends with a one-line remark.
export function BarCard({
  title,
  subtitle,
  items,
  note,
  labelWidth,
  className = "",
}: {
  title: string;
  subtitle: string;
  items: BarItem[];
  note: string;
  labelWidth?: string;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeading title={title} subtitle={subtitle} />
      <BarRows items={items} labelWidth={labelWidth} gap="gap-3" />
      <Note className="mt-auto">{note}</Note>
    </Card>
  );
}
