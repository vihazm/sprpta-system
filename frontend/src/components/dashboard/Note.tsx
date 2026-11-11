import type { ReactNode } from "react";

const TONES = {
  neutral: "bg-[#f7f4f5] text-muted",
  alert: "bg-red-50 text-red-800",
  rose: "bg-crimson/10 text-crimson-deep",
  good: "bg-emerald-50 text-emerald-900",
};

// A short boxed remark at the bottom of a card.
export function Note({
  tone = "neutral",
  children,
  className = "",
}: {
  tone?: keyof typeof TONES;
  children: ReactNode;
  className?: string;
}) {
  return (
    <p className={`rounded-[0.9rem] px-3 py-2.5 text-[0.78rem] leading-[1.45] ${TONES[tone]} ${className}`}>
      {children}
    </p>
  );
}
