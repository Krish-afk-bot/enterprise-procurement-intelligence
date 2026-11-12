import { useEffect, useRef } from "react";
import { loadScroll, motionAllowed } from "@/components/motion/scroll";

interface ScrollRevealOptions {
  /** Delay before animation starts (in seconds) */
  delay?: number;
  /** Animation duration (in seconds) */
  duration?: number;
  /** Distance to move from (in px) */
  y?: number;
  /** Start opacity */
  opacity?: number;
  /** Blur amount */
  blur?: number;
  /** ScrollTrigger start position */
  triggerStart?: string;
  /** Stagger for multiple elements */
  stagger?: number;
}

/**
 * Enhanced scroll reveal hook with GSAP ScrollTrigger.
 *
 * Returns a ref to attach to the element(s) you want to animate.
 * Supports single elements or multiple children with stagger.
 */
export function useScrollReveal<T extends HTMLElement>(options: ScrollRevealOptions = {}) {
  const {
    delay = 0,
    duration = 0.7,
    y = 30,
    opacity = 0,
    blur = 10,
    triggerStart = "top 80%",
    stagger = 0,
  } = options;

  const ref = useRef<T>(null);

  useEffect(() => {
    if (!motionAllowed()) return;

    const element = ref.current;
    if (!element) return;

    let cancelled = false;
    let context: { revert: () => void } | undefined;

    void loadScroll().then(({ gsap }) => {
      if (cancelled || !element) return;

      // Determine if we're animating the element or its children
      const targets = stagger > 0 ? element.children : element;

      context = gsap.context(() => {
        gsap.fromTo(
          targets,
          {
            opacity,
            y,
            filter: `blur(${blur}px)`,
          },
          {
            scrollTrigger: {
              trigger: element,
              start: triggerStart,
              toggleActions: "play none none none",
            },
            opacity: 1,
            y: 0,
            filter: "blur(0px)",
            duration,
            delay,
            stagger: stagger > 0 ? stagger : undefined,
            ease: "cubic-bezier(0.22, 1, 0.36, 1)",
          }
        );
      }, element);
    });

    return () => {
      cancelled = true;
      context?.revert();
    };
  }, [delay, duration, y, opacity, blur, triggerStart, stagger]);

  return ref;
}

/**
 * Staggered grid reveal - optimized for card grids.
 */
export function useGridReveal<T extends HTMLElement>() {
  return useScrollReveal<T>({
    y: 30,
    opacity: 0,
    blur: 10,
    duration: 0.7,
    stagger: 0.08,
    triggerStart: "top 85%",
  });
}

/**
 * Fade-only reveal (no movement) - for large sections.
 */
export function useFadeReveal<T extends HTMLElement>() {
  return useScrollReveal<T>({
    y: 0,
    opacity: 0,
    blur: 4,
    duration: 0.8,
  });
}
