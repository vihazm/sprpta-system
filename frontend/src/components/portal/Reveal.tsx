import type { ReactNode } from "react";

/**
 * Wraps a page's content, so it settles in softly when its data arrives and replaces the skeleton:
 * <Suspense fallback={<SomeSkeleton />}><Reveal><SomeContent /></Reveal></Suspense>
 */
export function Reveal({ children }: { children: ReactNode }) {
  return <div className="animate-reveal">{children}</div>;
}
