import { Note } from "@/components/dashboard/Note";
import { Card, CardHeading, Chip, LinkButton, PillButton, bigNumber, muted } from "@/components/dashboard/ui";
import { BAND_TONE } from "./bands";
import type { RatingRow } from "./types";

const th = "px-2 py-1.5 text-left text-[0.69rem] font-bold uppercase tracking-[0.07em] text-muted";

// Ratings of drivers, conductors and SPRPTA staff over the last 12 months (UC-L3-07).
export function TeamRatings({ ratings, className = "" }: { ratings: RatingRow[]; className?: string }) {
  return (
    <Card className={className}>
      <CardHeading
        title="Team ratings"
        subtitle="Drivers, conductors and SPRPTA staff · rolling 12 months · only substantiated complaints count"
        action={<LinkButton>Open all ratings</LinkButton>}
      />
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[0.78rem]">
          <thead>
            <tr>
              <th className={th}>Name</th>
              <th className={th}>Substantiated</th>
              <th className={th}>Pending</th>
              <th className={th}>Commendations</th>
              <th className={th}>Score</th>
              <th className={th}>Band</th>
              <th className={th}>
                <span className="sr-only">Details</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {ratings.map((r) => (
              <tr key={r.name} className="border-t border-[#f1ebed] font-bold">
                <td className="px-2 py-2.5">
                  <p className="text-[0.81rem] font-extrabold">{r.name}</p>
                  <p className={`${muted} font-medium`}>{r.role}</p>
                </td>
                <td className="px-2 py-2.5">{r.substantiated}</td>
                <td className="px-2 py-2.5">{r.pending}</td>
                <td className="px-2 py-2.5">{r.commendations}</td>
                <td className="px-2 py-2.5">
                  <span className={`${bigNumber} text-[1.25rem]`}>{r.score}</span>
                </td>
                <td className="px-2 py-2.5">
                  <Chip tone={BAND_TONE[r.band]}>{r.band}</Chip>
                </td>
                <td className="px-2 py-2.5 text-right">
                  <PillButton>Details</PillButton>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note>
        Partly substantiated counts as half. Pending complaints are listed but not counted. A rating is one input to
        award decisions, not the decision.
      </Note>
    </Card>
  );
}
