// Small inline icons for the notification pill (no icon library needed).

const base = {
  width: "100%",
  height: "100%",
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export function CheckIcon() {
  return (
    <svg {...base}>
      <path d="M5 12.5l4.5 4.5L19 7.5" />
    </svg>
  );
}

export function AlertIcon() {
  return (
    <svg {...base}>
      <path d="M12 6.5v7" />
      <path d="M12 17.6v.1" />
    </svg>
  );
}

export function CloseIcon() {
  return (
    <svg {...base} strokeWidth={2.2}>
      <path d="M6.5 6.5l11 11M17.5 6.5l-11 11" />
    </svg>
  );
}
