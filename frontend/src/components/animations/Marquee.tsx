import { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { cn } from "@/lib/utils";

interface MarqueeProps {
  items: string[];
  direction?: "left" | "right";
  speed?: number;
  className?: string;
}

export function Marquee({
  items,
  direction = "left",
  speed = 40,
  className,
}: MarqueeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const reducedMotion = useReducedMotion();

  useLayoutEffect(() => {
    if (reducedMotion || !trackRef.current) return;

    const track = trackRef.current;
    const distance = track.scrollWidth / 2;
    const duration = distance / speed;

    const ctx = gsap.context(() => {
      const fromX = direction === "left" ? 0 : -distance;
      const toX = direction === "left" ? -distance : 0;

      gsap.fromTo(
        track,
        { x: fromX },
        {
          x: toX,
          duration,
          ease: "none",
          repeat: -1,
        }
      );
    }, track);

    return () => ctx.revert();
  }, [items, direction, speed, reducedMotion]);

  // Duplicate items for continuous seamless loop
  const displayItems = [...items, ...items, ...items];

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative w-full overflow-hidden whitespace-nowrap [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]",
        className
      )}
    >
      <div
        ref={trackRef}
        className="inline-flex gap-3 py-2 transform-gpu will-change-transform"
      >
        {displayItems.map((item, idx) => (
          <span
            key={`${item}-${idx}`}
            className="inline-flex items-center px-4 py-2 rounded-full text-xs font-medium tracking-wide bg-black/5 text-[#0A0A0A] border border-black/10 backdrop-blur-sm select-none hover:border-[#FF4D00]/40 transition-colors"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#FF4D00] mr-2 inline-block opacity-80" />
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
