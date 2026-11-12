import { useEffect, useRef } from "react";
import { loadScroll, motionAllowed } from "@/components/motion/scroll";

interface WordRevealProps {
  children: string;
  className?: string;
  /** Time-based (hero) or scroll-based (sections) */
  mode?: "time" | "scroll";
  /** Base delay in ms (time mode) */
  delay?: number;
  /** Stagger between words in seconds */
  stagger?: number;
  /** Duration of each word animation in seconds */
  duration?: number;
  /** Optional trigger element for scroll mode */
  triggerRef?: React.RefObject<HTMLElement>;
  as?: "h1" | "h2" | "h3" | "p";
}

/**
 * Word-by-word reveal animation.
 *
 * Each word starts dim, blurred, and slightly below position, then animates
 * to full opacity, sharp, and in position. The effect establishes hierarchy
 * and draws attention to key messaging.
 *
 * **Time mode**: Animates automatically on mount (hero).
 * **Scroll mode**: Animates when scrolled into view (section headings).
 */
export function WordReveal({
  children,
  className = "",
  mode = "scroll",
  delay = 0,
  stagger = 0.08,
  duration = 0.8,
  triggerRef,
  as: Component = "h2",
}: WordRevealProps) {
  const containerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!motionAllowed()) return;

    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    let context: { revert: () => void } | undefined;

    void loadScroll().then(({ gsap }) => {
      if (cancelled || !container) return;

      const words = container.querySelectorAll(".word-reveal-item");
      if (words.length === 0) return;

      // Initial state: dim, blurred, below position
      gsap.set(words, {
        opacity: 0.15,
        filter: "blur(6px)",
        y: 24,
        color: "#71717A", // Subtle grey
      });

      if (mode === "time") {
        // Time-based animation for hero
        context = gsap.context(() => {
          gsap.to(words, {
            opacity: 1,
            filter: "blur(0px)",
            y: 0,
            color: "inherit",
            duration,
            stagger,
            delay: delay / 1000,
            ease: "cubic-bezier(0.22, 1, 0.36, 1)",
          });
        }, container);
      } else {
        // Scroll-based animation for sections
        const trigger = triggerRef?.current || container;

        context = gsap.context(() => {
          gsap.to(words, {
            scrollTrigger: {
              trigger,
              start: "top 80%",
              toggleActions: "play none none none",
            },
            opacity: 1,
            filter: "blur(0px)",
            y: 0,
            color: "inherit",
            duration,
            stagger,
            ease: "cubic-bezier(0.22, 1, 0.36, 1)",
          });
        }, container);
      }
    });

    return () => {
      cancelled = true;
      context?.revert();
    };
  }, [mode, delay, stagger, duration, triggerRef]);

  // Split text into words while preserving spaces
  const words = children.split(" ").filter((word) => word.length > 0);

  return (
    <Component ref={containerRef as React.RefObject<any>} className={className}>
      {words.map((word, index) => (
        <span key={`${word}-${index}`} className="word-reveal-item inline-block" style={{ whiteSpace: "pre" }}>
          {word}
          {index < words.length - 1 ? " " : ""}
        </span>
      ))}
    </Component>
  );
}

/**
 * Reduced motion fallback: renders text normally.
 */
export function WordRevealStatic({ children, className = "", as: Component = "h2" }: Pick<WordRevealProps, "children" | "className" | "as">) {
  return <Component className={className}>{children}</Component>;
}
