// The few icons the Users page needs, drawn on a 24px grid.

const PATHS = {
  search: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-3.5-3.5",
  plus: "M12 5v14M5 12h14",
  edit: "M4 20h4L20 8l-4-4L4 16v4z",
  close: "M6 6l12 12M18 6L6 18",
  prev: "M15 6l-6 6 6 6",
  next: "M9 6l6 6-6 6",
};

export function Icon({ name, size = 15 }: { name: keyof typeof PATHS; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.3"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
