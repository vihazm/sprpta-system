import { AreaChart } from "./AreaChart";
import { Card, CardHeading, PillButton } from "./ui";

const hourLabel = (hour: number) => `${String(hour).padStart(2, "0")}:00`;

export function SignInRhythm({
  perHour,
  currentHour,
  className = "",
}: {
  perHour: number[];
  currentHour: number;
  className?: string;
}) {
  // perHour ends with the current hour, so work backwards to name each bar.
  const hourAt = (index: number) => (currentHour - (perHour.length - 1 - index) + 24) % 24;
  const peakIndex = perHour.indexOf(Math.max(...perHour));
  const peakLeft = (peakIndex / (perHour.length - 1)) * 100;
  const hasSignIns = perHour[peakIndex] > 0;

  return (
    <Card className={className}>
      <CardHeading
        title="Sign-in rhythm"
        subtitle="Sign-ins per hour, last 24 hours"
        action={<PillButton>Usage logs</PillButton>}
      />

      <div className="relative">
        <AreaChart
          values={perHour}
          markers={hasSignIns ? [peakIndex] : []}
          label={
            hasSignIns
              ? `Sign-ins per hour. The peak was ${perHour[peakIndex]} at ${hourLabel(hourAt(peakIndex))}.`
              : "No sign-ins in the last 24 hours."
          }
          className="h-[11.5rem] border-b border-slate-200 text-crimson"
        />
        {hasSignIns && (
          <span
            className="absolute top-0 mr-4 rounded-full bg-crimson px-[0.7rem] py-[0.2rem] text-[0.72rem] font-bold text-white"
            style={{ right: `${100 - peakLeft}%` }}
          >
            {hourLabel(hourAt(peakIndex))} peak, {perHour[peakIndex]}
          </span>
        )}
      </div>

      <div className="flex justify-between text-[0.69rem] font-semibold text-muted">
        {[0, 6, 12, 18].map((i) => (
          <span key={i}>{hourLabel(hourAt(i))}</span>
        ))}
        <span>Now</span>
      </div>
    </Card>
  );
}
