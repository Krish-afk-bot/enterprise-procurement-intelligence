import { useEffect, useState } from "react";

/**
 * True when the operating system asks for reduced motion. Scenes use this to
 * render a single static frame instead of animating.
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() =>
    typeof window === "undefined" ? true : window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  return reduced;
}
