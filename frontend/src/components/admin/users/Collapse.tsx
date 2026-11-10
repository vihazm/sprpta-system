import type { ReactNode } from "react";

// Slides its content open or shut by animating the row height from 0fr to 1fr.
// A shut section is inert, so keyboard focus cannot reach it.
export function Collapse({ show, children }: { show: boolean; children: ReactNode }) {
  return (
    <div
      inert={!show}
      className={`grid transition-[grid-template-rows,opacity] duration-[360ms] ease-in-out motion-reduce:transition-none ${
        show ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
      }`}
    >
      <div className="min-h-0 overflow-hidden">
        <div className="flex flex-col gap-4 pb-4">{children}</div>
      </div>
    </div>
  );
}
