import { useEffect, useRef } from "react";
import { canPin, loadScroll } from "@/components/motion/scroll";

interface CurtainTransitionProps {
  /** Which theme this section has */
  theme: "dark" | "light";
  /** Section ref to trigger on */
  triggerRef: React.RefObject<HTMLElement>;
  /** Callback when theme changes (for navbar sync) */
  onThemeChange?: (theme: "dark" | "light") => void;
}

/**
 * Curtain transition between dark and light sections.
 *
 * A full-width panel rises from the bottom to cover the previous section,
 * creating a cinematic wipe effect. Coordinates with navbar theme changes.
 *
 * **Dark to light**: Off-white sheet rises
 * **Light to dark**: Black sheet rises
 */
export function CurtainTransition({ theme, triggerRef, onThemeChange }: CurtainTransitionProps) {
  const curtainRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!canPin()) return;

    const curtain = curtainRef.current;
    const trigger = triggerRef.current;
    if (!curtain || !trigger) return;

    let cancelled = false;
    let context: { revert: () => void } | undefined;

    void loadScroll().then(({ gsap, ScrollTrigger }) => {
      if (cancelled) return;

      context = gsap.context(() => {
        ScrollTrigger.create({
          trigger,
          start: "top 80%",
          end: "top 20%",
          onEnter: () => onThemeChange?.(theme),
          onEnterBack: () => {
            // When scrolling back up, restore previous theme
            const prevTheme = theme === "dark" ? "light" : "dark";
            onThemeChange?.(prevTheme);
          },
        });

        gsap.fromTo(
          curtain,
          {
            yPercent: 100,
          },
          {
            scrollTrigger: {
              trigger,
              start: "top bottom",
              end: "top 60%",
              scrub: 0.8,
            },
            yPercent: 0,
            ease: "none",
          }
        );
      });
    });

    return () => {
      cancelled = true;
      context?.revert();
    };
  }, [theme, triggerRef, onThemeChange]);

  const curtainBg = theme === "light" ? "bg-[#FAFAF9]" : "bg-ink";

  return (
    <div ref={curtainRef} className={`pointer-events-none absolute inset-x-0 top-0 h-full ${curtainBg}`} aria-hidden="true" />
  );
}
