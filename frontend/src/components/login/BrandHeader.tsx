export function BrandHeader() {
  return (
    <div className="flex items-center gap-[0.8rem]">
      <div className="flex h-[2.75rem] w-[2.75rem] flex-none items-center justify-center rounded-[0.8rem] bg-[#A8102F]">
        <svg
          width="26"
          height="26"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <rect x="4" y="3" width="16" height="14" rx="3" />
          <path d="M4 11h16" />
          <circle cx="8" cy="19.5" r="1.5" />
          <circle cx="16" cy="19.5" r="1.5" />
        </svg>
      </div>
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
