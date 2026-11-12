import { useEffect, useState } from "react";

/**
 * Track scroll progress through the document (0–1).
 *
 * Returns the current scroll progress and whether the page is near the top.
 * Updates are throttled to avoid excessive re-renders.
 */
export function useScrollProgress() {
  const [progress, setProgress] = useState(0);
  const [isAtTop, setIsAtTop] = useState(true);

  useEffect(() => {
    let ticking = false;

    const update = () => {
      const scrolled = window.scrollY;
      const height = document.documentElement.scrollHeight - window.innerHeight;
      const newProgress = height > 0 ? Math.min(scrolled / height, 1) : 0;
      const newAtTop = scrolled < 80;

      setProgress(newProgress);
      setIsAtTop(newAtTop);
      ticking = false;
    };

    const onScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(update);
        ticking = true;
      }
    };

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return { progress, isAtTop };
}
