import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Reveal — a scroll-triggered entrance.
 *
 * Deliberately dependency-free: an IntersectionObserver adds one class and CSS
 * does the rest, so the effect costs no runtime animation loop and animates only
 * `opacity` / `transform`. Content is never left hidden: if the observer is
 * unavailable, or the reader asked for reduced motion, the element renders in
 * its final state immediately (the reduced-motion rule in `index.css` also
 * forces `.reveal` visible as a second guard).
 *
 * `delay` staggers siblings; keep the group small so a page does not feel slow.
 */
export function Reveal({
  children,
  className,
  delay = 0,
  as: As = "div",
  once = true,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  as?: "div" | "section" | "li" | "article" | "header" | "figure";
  once?: boolean;
}) {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true);
            if (once) observer.disconnect();
          } else if (!once) {
            setVisible(false);
          }
        }
      },
      // Start a little before the element enters: the motion finishes as it
      // settles into view rather than after it.
      { rootMargin: "0px 0px -12% 0px", threshold: 0.08 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [once]);

  return (
    <As
      ref={ref as never}
      className={cn("reveal", visible && "is-visible", className)}
      style={delay ? ({ "--reveal-delay": `${delay}ms` } as React.CSSProperties) : undefined}
    >
      {children}
    </As>
  );
}
