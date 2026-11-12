import { useEffect, useRef } from "react";
import { loadScroll, motionAllowed } from "@/components/motion/scroll";

interface MarqueeProps {
  children: React.ReactNode;
  /** Direction of movement */
  direction?: "left" | "right";
  /** Speed in pixels per second */
  speed?: number;
  /** Pause on hover */
  pauseOnHover?: boolean;
  className?: string;
}

/**
 * Infinite horizontal marquee.
 *
 * Content is duplicated to create seamless loop. Used for capability chips
 * in the explainer section.
 */
export function Marquee({ children, direction = "left", speed = 30, pauseOnHover = true, className = "" }: MarqueeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const animationRef = useRef<gsap.core.Tween | null>(null);

  useEffect(() => {
    if (!motionAllowed()) return;

    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    let context: { revert: () => void } | undefined;

    void loadScroll().then(({ gsap }) => {
      if (cancelled || !container) return;

      const track = container.querySelector(".marquee-track") as HTMLElement;
      if (!track) return;

      // Measure the width of one set of items
      const firstItem = track.firstElementChild as HTMLElement;
      if (!firstItem) return;

      const itemWidth = firstItem.offsetWidth;
      const duration = itemWidth / speed;

      // Create infinite animation
      context = gsap.context(() => {
        const xPercent = direction === "left" ? -50 : 50;
        const startPercent = direction === "left" ? 0 : -50;

        gsap.set(track, { xPercent: startPercent });

        animationRef.current = gsap.to(track, {
          xPercent,
          duration,
          ease: "none",
          repeat: -1,
          modifiers: {
            xPercent: gsap.utils.wrap(startPercent, xPercent),
          },
        });
      }, container);
    });

    return () => {
      cancelled = true;
      context?.revert();
      if (animationRef.current) {
        animationRef.current.kill();
      }
    };
  }, [direction, speed]);

  const handleMouseEnter = () => {
    if (pauseOnHover && animationRef.current) {
      animationRef.current.pause();
    }
  };

  const handleMouseLeave = () => {
    if (pauseOnHover && animationRef.current) {
      animationRef.current.play();
    }
  };

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="marquee-track flex gap-3 will-change-transform">
        {/* Duplicate content for seamless loop */}
        <div className="flex shrink-0 gap-3">{children}</div>
        <div className="flex shrink-0 gap-3" aria-hidden="true">
          {children}
        </div>
      </div>
    </div>
  );
}

/**
 * Marquee chip: individual capability badge.
 */
export function MarqueeChip({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-[12px] font-medium tracking-wide backdrop-blur-sm ${className}`}
    >
      {children}
    </span>
  );
}
