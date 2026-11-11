import { SeverityChip } from "@/components/dashboard/severity";
import { Card, CardHeading } from "@/components/dashboard/ui";
import type { TimeTarget } from "./types";

const th = "px-2 py-1.5 text-left text-[0.69rem] font-bold uppercase tracking-[0.07em] text-muted";

// How long each step may take, counted in days from registration. Admin can change the values.
export function TimeTargets({ targets, className = "" }: { targets: TimeTarget[]; className?: string }) {
  return (
    <Card className={className}>
      <CardHeading title="Time targets" subtitle="Counted from registration. Passing one raises an Overdue flag." />
      <table className="w-full border-collapse text-[0.78rem]">
        <thead>
          <tr>
            <th className={th}>Severity</th>
            <th className={th}>Forward by</th>
            <th className={th}>Decide by</th>
            <th className={th}>Close by</th>
          </tr>
        </thead>
        <tbody>
          {targets.map((t) => (
            <tr key={t.severity} className="border-t border-[#f1ebed] font-bold">
              <td className="px-2 py-2.5">
                <SeverityChip severity={t.severity} />
              </td>
              <td className="px-2 py-2.5">{t.forward}</td>
              <td className="px-2 py-2.5">{t.decide}</td>
              <td className="px-2 py-2.5">{t.close}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
