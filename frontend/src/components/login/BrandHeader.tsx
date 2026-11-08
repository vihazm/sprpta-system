import { BrandTile } from "@/components/BrandTile";

export function BrandHeader() {
  return (
    <div className="flex items-center gap-[0.8rem]">
      <BrandTile />
      <div className="flex min-w-0 flex-col gap-0.5">
        <div className="text-[1.2rem] font-extrabold leading-[1.2] tracking-[0.04em] text-slate-ink">
          SPRPTA
        </div>
        <div className="text-[0.86rem] font-medium leading-[1.3] text-slate-muted">
          Complaint &amp; Recommendation Management System
        </div>
      </div>
    </div>
  );
}
