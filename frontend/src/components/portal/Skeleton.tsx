import type { ReactNode } from "react";
import { Card } from "@/components/dashboard/ui";

// The pieces the page skeletons (PageSkeletons.tsx) are built from. They use the same cards, radii, spacing and
// grid as the real pages, so nothing moves when the content arrives.

/** One placeholder block. Give it a size, for example "h-4 w-40". */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`skeleton rounded-[0.6rem] bg-[#f1ebed] ${className}`} />;
}

/** Placeholder text lines, the last one shorter. */
export function SkeletonLines({ count = 3, className = "" }: { count?: number; className?: string }) {
  return (
    <div className={`flex flex-col gap-2.5 ${className}`}>
      {Array.from({ length: count }, (_, i) => (
        <Skeleton key={i} className={`h-3.5 ${i === count - 1 && count > 1 ? "w-3/5" : "w-full"}`} />
      ))}
    </div>
  );
}

/** A white card with a title bar and a body of the given minimum height, for example "min-h-[12rem]". */
export function SkeletonCard({ height = "min-h-[11rem]", className = "" }: { height?: string; className?: string }) {
  return (
    <Card className={`${height} ${className}`}>
      <Skeleton className="h-5 w-2/5" />
      <SkeletonLines count={3} />
    </Card>
  );
}

/** The crimson banner at the top of the dashboards, in a pale rose. */
export function SkeletonHero() {
  return (
    <div
      aria-hidden="true"
      className="flex flex-wrap justify-between gap-[1.6rem] rounded-[2rem] bg-gradient-to-br from-[#f4e3e8] to-[#faf1f3] p-[1.9rem]"
    >
      <div className="flex min-w-0 flex-[1_1_23rem] flex-col justify-between gap-5">
        <div className="flex flex-col gap-3">
          <Skeleton className="h-3 w-36 !bg-white/70" />
          <Skeleton className="h-[2.6rem] w-4/5 !bg-white/70" />
          <Skeleton className="h-[2.6rem] w-3/5 !bg-white/70" />
          <Skeleton className="mt-1 h-3.5 w-[22rem] max-w-full !bg-white/70" />
        </div>
        <div className="flex flex-wrap gap-2.5">
          <Skeleton className="h-[2.6rem] w-44 !rounded-full !bg-white/80" />
          <Skeleton className="h-[2.6rem] w-44 !rounded-full !bg-white/80" />
        </div>
      </div>
      <div className="flex min-w-[18rem] flex-[0_1_26rem] flex-col gap-3.5 rounded-[1.6rem] bg-white/50 p-5">
        <Skeleton className="h-3 w-28 !bg-white" />
        <div className="grid grid-cols-3 gap-2.5">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-[5.2rem] !rounded-[1.1rem] !bg-white/80" />
          ))}
        </div>
        <Skeleton className="h-3 w-2/3 !bg-white" />
      </div>
    </div>
  );
}

// Tailwind only creates classes it can see written out in full, so the spans are listed here.
const SPAN = {
  3: "min-[1200px]:col-span-3",
  4: "min-[1200px]:col-span-4",
  5: "min-[1200px]:col-span-5",
  6: "min-[1200px]:col-span-6",
  7: "min-[1200px]:col-span-7",
  8: "min-[1200px]:col-span-8",
  12: "min-[1200px]:col-span-12",
} as const;

/** One cell of the bento grid: how many of the 12 columns it spans, and its minimum height. */
export type Cell = [span: keyof typeof SPAN, height: string];

/** The 12-column grid the dashboards use (one column on narrow screens), filled with placeholder cards. */
export function SkeletonGrid({ cells }: { cells: Cell[] }): ReactNode {
  return (
    <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
      {cells.map(([span, height], i) => (
        <SkeletonCard key={i} height={height} className={SPAN[span]} />
      ))}
    </div>
  );
}
