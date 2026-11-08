/** The crimson bus tile used in the login header and the signed-in header. */
export function BrandTile({ size = "2.75rem" }: { size?: string }) {
  return (
    <div
      style={{ width: size, height: size }}
      className="flex flex-none items-center justify-center rounded-[0.8rem] bg-[#A8102F]"
    >
      <svg
        width="58%"
        height="58%"
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
  );
}
