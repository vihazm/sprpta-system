import { Card } from "@/components/dashboard/ui";
import { Skeleton, SkeletonCard, SkeletonGrid, SkeletonHero, type Cell } from "./Skeleton";

// What each page shows in its place while its data loads. Each one follows the layout of the page it stands in
// for. When you build a new page, add its skeleton here and use it as the Suspense fallback of the page.

const stack = "flex flex-col gap-4";

/** A page's section heading, for example "Today at a glance". */
function HeadingBar() {
  return <Skeleton className="h-6 w-56" />;
}

/** A row of tab-like pills. */
function PillRow({ count = 5 }: { count?: number }) {
  return (
    <div className="flex flex-wrap gap-2">
      {Array.from({ length: count }, (_, i) => (
        <Skeleton key={i} className="h-8 w-24 !rounded-full" />
      ))}
    </div>
  );
}

/** A search box and a table of rows, as in the complaints and daily records lists. */
function TableCard({ rows = 8 }: { rows?: number }) {
  return (
    <Card className="min-h-[30rem]">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-3.5 w-3/5" />
      </div>
      <PillRow />
      <Skeleton className="h-10 w-full max-w-[26rem] !rounded-full" />
      <div className="flex flex-col gap-2">
        {Array.from({ length: rows }, (_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    </Card>
  );
}

/** A form: a title and a few rows of fields. */
function FormCard({ rows = 5, className = "" }: { rows?: number; className?: string }) {
  return (
    <Card className={className}>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-6 w-56" />
        <Skeleton className="h-3.5 w-4/5" />
      </div>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="grid gap-3 min-[900px]:grid-cols-2">
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-11 w-full" />
        </div>
      ))}
      <Skeleton className="h-11 w-40 !rounded-full" />
    </Card>
  );
}

// ---------------------------------------------------------------- dashboards

const adminDashboard: Cell[] = [
  [8, "min-h-[17rem]"], [4, "min-h-[17rem]"],
  [4, "min-h-[13rem]"], [8, "min-h-[13rem]"],
  [7, "min-h-[14rem]"], [5, "min-h-[14rem]"],
  [3, "min-h-[11rem]"], [3, "min-h-[11rem]"], [3, "min-h-[11rem]"], [3, "min-h-[11rem]"],
  [8, "min-h-[14rem]"], [4, "min-h-[14rem]"],
];

export function AdminDashboardSkeleton() {
  return (
    <div className={stack}>
      <HeadingBar />
      <SkeletonGrid cells={adminDashboard} />
    </div>
  );
}

const systemHealth: Cell[] = [
  [8, "min-h-[17rem]"], [4, "min-h-[17rem]"],
  [4, "min-h-[11rem]"], [4, "min-h-[11rem]"], [4, "min-h-[11rem]"],
  [3, "min-h-[11rem]"], [3, "min-h-[11rem]"], [3, "min-h-[11rem]"], [3, "min-h-[11rem]"],
  [7, "min-h-[14rem]"], [5, "min-h-[14rem]"],
];

export function SystemHealthSkeleton() {
  return (
    <div className={stack}>
      <HeadingBar />
      <SkeletonGrid cells={systemHealth} />
    </div>
  );
}

export function UsersSkeleton() {
  return (
    <div className={stack}>
      <SkeletonGrid cells={[[8, "min-h-[10rem]"], [4, "min-h-[10rem]"]]} />
      <TableCard rows={6} />
    </div>
  );
}

export function MasterDataSkeleton() {
  return (
    <div className={stack}>
      <HeadingBar />
      <SkeletonGrid cells={Array.from({ length: 8 }, (): Cell => [3, "min-h-[10.5rem]"])} />
    </div>
  );
}

export function RecordsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
      <div className="min-[1200px]:col-span-8">
        <TableCard rows={6} />
      </div>
      <SkeletonCard height="min-h-[12rem]" className="self-start min-[1200px]:col-span-4" />
    </div>
  );
}

export function MessageTemplatesSkeleton() {
  return (
    <div className={stack}>
      <HeadingBar />
      {Array.from({ length: 2 }, (_, i) => (
        <SkeletonCard key={i} height="min-h-[26rem]" />
      ))}
    </div>
  );
}

const statistics: Cell[] = [
  [12, "min-h-[9rem]"],
  [12, "min-h-[7rem]"],
  [6, "min-h-[16rem]"], [6, "min-h-[16rem]"],
  [4, "min-h-[14rem]"], [4, "min-h-[14rem]"], [4, "min-h-[14rem]"],
  [4, "min-h-[16rem]"], [8, "min-h-[16rem]"],
];

export function StatisticsSkeleton() {
  return <SkeletonGrid cells={statistics} />;
}

const l1Dashboard: Cell[] = [
  [8, "min-h-[32rem]"], [4, "min-h-[32rem]"],
  [12, "min-h-[8rem]"],
  [12, "min-h-[16rem]"],
  [4, "min-h-[18rem]"], [4, "min-h-[18rem]"], [4, "min-h-[18rem]"],
  [7, "min-h-[14rem]"], [5, "min-h-[14rem]"],
  [12, "min-h-[10rem]"],
];

const l2Dashboard: Cell[] = [
  [12, "min-h-[7rem]"],
  [8, "min-h-[36rem]"], [4, "min-h-[36rem]"],
  [4, "min-h-[16rem]"], [4, "min-h-[16rem]"], [4, "min-h-[16rem]"],
];

const l3Dashboard: Cell[] = [
  [8, "min-h-[20rem]"], [4, "min-h-[20rem]"],
  [4, "min-h-[16rem]"], [4, "min-h-[16rem]"], [4, "min-h-[16rem]"],
  [4, "min-h-[14rem]"], [4, "min-h-[14rem]"], [4, "min-h-[14rem]"],
  [6, "min-h-[14rem]"], [6, "min-h-[14rem]"],
  [8, "min-h-[16rem]"], [4, "min-h-[16rem]"],
  [5, "min-h-[14rem]"], [7, "min-h-[14rem]"],
  [5, "min-h-[14rem]"], [7, "min-h-[14rem]"],
];

function HeroDashboard({ cells }: { cells: Cell[] }) {
  return (
    <div className={stack}>
      <SkeletonHero />
      <SkeletonGrid cells={cells} />
    </div>
  );
}

export const L1DashboardSkeleton = () => <HeroDashboard cells={l1Dashboard} />;
export const L2DashboardSkeleton = () => <HeroDashboard cells={l2Dashboard} />;
export const L3DashboardSkeleton = () => <HeroDashboard cells={l3Dashboard} />;

// ---------------------------------------------------------------- Level 1 screens

export const ComplaintsSkeleton = () => <TableCard />;

export function BusLookupSkeleton() {
  return (
    <div className={stack}>
      <SkeletonCard height="min-h-[16rem]" />
      <TableCard rows={5} />
    </div>
  );
}

export const NewComplaintSkeleton = () => <FormCard rows={6} />;

export const RecommendationSkeleton = () => <FormCard rows={3} className="max-w-[44rem]" />;

// ---------------------------------------------------------------- Level 2 screens

export const CasesSkeleton = () => <TableCard />;
export const RecommendationsSkeleton = () => <TableCard rows={6} />;

export function CaseReviewSkeleton() {
  return (
    <div className={stack}>
      <SkeletonCard height="min-h-[9rem]" />
      <SkeletonGrid cells={[[8, "min-h-[30rem]"], [4, "min-h-[30rem]"]]} />
    </div>
  );
}

// ---------------------------------------------------------------- Complainant screens

export function CpDashboardSkeleton() {
  return (
    <div className={stack}>
      <Skeleton className="h-3 w-44" />
      <Skeleton className="h-[2.6rem] w-80 max-w-full" />
      <SkeletonCard height="min-h-[5rem]" />
      <SkeletonGrid cells={[[4, "min-h-[8rem]"], [4, "min-h-[8rem]"], [4, "min-h-[8rem]"]]} />
      <SkeletonGrid cells={[[8, "min-h-[18rem]"], [4, "min-h-[18rem]"]]} />
    </div>
  );
}

export const CpFormSkeleton = () => <FormCard rows={6} className="max-w-[56rem]" />;

export function CpComplaintsSkeleton() {
  return (
    <div className={stack}>
      <Skeleton className="h-3 w-32" />
      <Skeleton className="h-[2.4rem] w-64 max-w-full" />
      <SkeletonGrid cells={[[5, "min-h-[26rem]"], [7, "min-h-[26rem]"]]} />
    </div>
  );
}
