import { STEPS, formatDate } from "./status";
import type { PortalComplaint } from "./types";

/** The four steps of one complaint, top to bottom: finished ones in green, the current one in crimson. */
export function StatusTimeline({ complaint }: { complaint: PortalComplaint }) {
  const finished = complaint.step === 4;
  return (
    <ol className="m-0 list-none p-0">
      {STEPS.map((step, i) => {
        const n = i + 1;
        const done = n < complaint.step || finished;
        const current = n === complaint.step && !finished;
        const date = done || current ? formatDate(complaint.stepDates[i]) : "";
        const label = n === 4 && complaint.outcome === "not_accepted" ? "Closed (not accepted)" : step.label;
        return (
          <li key={step.label} className="flex gap-[1rem]" aria-current={current ? "step" : undefined}>
            <div className="flex w-[2.1rem] flex-none flex-col items-center">
              <span
                className={`grid size-[2.1rem] place-items-center rounded-full text-[0.86rem] font-extrabold ${
                  done
                    ? "bg-emerald-700 text-white"
                    : current
                      ? "bg-crimson text-white shadow-[0_0_0_0.4rem_rgba(179,17,47,0.14)]"
                      : "bg-[#e5e1e3] text-slate-muted"
                }`}
              >
                {done ? "✓" : n}
              </span>
              {n < STEPS.length && (
                <span className={`min-h-[2rem] w-[3px] flex-1 rounded-full ${done ? "bg-emerald-700" : "bg-[#e5e1e3]"}`} />
              )}
            </div>
            <div className="pb-[1.3rem] pt-[0.3rem]">
              <p className="m-0 text-[0.94rem] font-extrabold">
                {label}
                <span className="sr-only">{done ? " (done)" : current ? " (current step)" : " (not reached yet)"}</span>
              </p>
              <p className="m-0 mt-[0.15rem] text-[0.8rem] leading-[1.45] text-muted">
                {done || current ? step.note : "Not reached yet."}
                {date && <span className="font-bold text-slate-ink"> · {date}</span>}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
