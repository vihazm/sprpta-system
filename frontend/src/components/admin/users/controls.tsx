import type { ReactNode } from "react";

// Form controls shared by the directory filters and the edit panel.

export const inputClass =
  "focus-ring h-11 w-full rounded-[0.9rem] border-[1.5px] border-transparent bg-field px-[0.9rem] text-[0.88rem] font-medium text-ink focus:border-crimson focus:bg-white";

export const iconButton =
  "focus-ring inline-flex size-[2.1rem] flex-none cursor-pointer items-center justify-center rounded-full border-[1.5px] border-[#E5E7EB] bg-white text-[0.78rem] font-bold text-slate-600 transition-colors hover:border-crimson hover:text-crimson";

export function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-[0.4rem]">
      <label htmlFor={htmlFor} className="text-[0.78rem] font-bold text-ink">
        {label}
      </label>
      {children}
    </div>
  );
}
