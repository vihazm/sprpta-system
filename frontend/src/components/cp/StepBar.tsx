import type { PortalComplaint } from "./types";

/** Four thin segments showing how far a complaint has come. Finished steps are green, the current one crimson. */
export function StepBar({ complaint, className = "" }: { complaint: PortalComplaint; className?: string }) {
  const finished = complaint.step === 4;
  return (
    <div
      role="img"
      aria-label={`Step ${complaint.step} of 4: ${complaint.statusLabel}`}
      className={`flex gap-[0.3rem] ${className}`}
    >
      {[1, 2, 3, 4].map((n) => (
        <span
          key={n}
          className={`h-[0.4rem] flex-1 rounded-full ${
            n < complaint.step || finished ? "bg-emerald-700" : n === complaint.step ? "bg-crimson" : "bg-[#e5e1e3]"
          }`}
        />
      ))}
    </div>
  );
}
