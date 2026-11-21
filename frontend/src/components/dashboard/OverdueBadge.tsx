// Shown on a case whose forward-by, decide-by or close-by time target has passed. A flag only: it is never a
// status and nothing happens automatically (UI Flow 7).
export function OverdueBadge() {
  return (
    <span className="inline-flex whitespace-nowrap rounded-full bg-crimson px-[0.55rem] py-[0.15rem] text-[0.66rem] font-extrabold text-white">
      Overdue
    </span>
  );
}
