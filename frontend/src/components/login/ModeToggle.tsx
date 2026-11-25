import type { ReactNode } from "react";
import type { AuthMode } from "@/lib/validators";

/** The Email / Phone switch shared by the sign-in and sign-up forms. */
export function ModeToggle({
  mode,
  onChange,
  label,
}: {
  mode: AuthMode;
  onChange: (mode: AuthMode) => void;
  label: string;
}) {
  const isEmail = mode === "email";
  return (
    <div
      role="group"
      aria-label={label}
      className="relative grid grid-cols-2 rounded-full bg-field p-[0.3rem]"
    >
      <span
        aria-hidden="true"
        className={`absolute bottom-[0.3rem] left-[0.3rem] top-[0.3rem] w-[calc(50%-0.3rem)] rounded-full bg-ink transition-transform duration-[280ms] ease-[cubic-bezier(.3,.9,.3,1)] ${
          isEmail ? "" : "translate-x-full"
        }`}
      />
      <ToggleButton active={isEmail} label="Email" onClick={() => onChange("email")}>
        <svg {...ICON} aria-hidden="true">
          <rect x="3" y="5" width="18" height="14" rx="2.5" />
          <path d="M3.5 7l8.5 6 8.5-6" />
        </svg>
      </ToggleButton>
      <ToggleButton active={!isEmail} label="Phone" onClick={() => onChange("phone")}>
        <svg {...ICON} aria-hidden="true">
          <rect x="7" y="2.5" width="10" height="19" rx="2.5" />
          <path d="M11 18.5h2" />
        </svg>
      </ToggleButton>
    </div>
  );
}

const ICON = {
  width: 17,
  height: 17,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.9,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

function ToggleButton({
  active,
  label,
  onClick,
  children,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`focus-ring relative z-10 flex h-[2.6rem] cursor-pointer items-center justify-center gap-2 rounded-full text-[0.92rem] font-bold transition-colors duration-200 ${
        active ? "text-white" : "text-muted"
      }`}
    >
      {children}
      {label}
    </button>
  );
}
