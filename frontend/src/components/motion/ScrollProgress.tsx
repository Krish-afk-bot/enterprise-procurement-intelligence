import { useScrollProgress } from "@/lib/useScrollProgress";
import { cn } from "@/lib/utils";

/**
 * Global scroll progress indicator — a hairline that fills as you scroll down.
 *
 * Fixed to the top of the viewport, hidden on the landing page hero (first screen),
 * and never shown for reduced motion. Pure visual feedback; does not navigate.
 */
export function ScrollProgress({ className }: { className?: string }) {
  const { progress, isAtTop } = useScrollProgress();

  const reduce = typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reduce || isAtTop) return null;

  return (
    <div
      className={cn(
        "fixed left-0 right-0 top-0 z-50 h-[1px] overflow-hidden bg-white/10",
        className,
      )}
      aria-hidden="true"
    >
      <span
        className="block h-full origin-left bg-gradient-to-r from-white/70 to-white/90 transition-transform duration-150 ease-out"
        style={{ transform: `scaleX(${progress})` }}
      />
    </div>
  );
}
