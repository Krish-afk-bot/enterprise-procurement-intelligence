import React, { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { cn } from "@/lib/utils";
import { useReducedMotion } from "@/hooks/useReducedMotion";

gsap.registerPlugin(ScrollTrigger);

interface CurtainTransitionProps {
  from: "dark" | "light";
  to: "dark" | "light";
  children: React.ReactNode;
  className?: string;
  id?: string;
}

export function CurtainTransition({
  from = "dark",
  to,
  children,
  className,
  id,
}: CurtainTransitionProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sheetRef = useRef<HTMLDivElement>(null);
  const reducedMotion = useReducedMotion();

  useLayoutEffect(() => {
    if (reducedMotion || !containerRef.current || !sheetRef.current) return;

    const container = containerRef.current;
    const sheet = sheetRef.current;

    const ctx = gsap.context(() => {
      // Solid opaque sheet slides up with 32px rounded top edge, scrubbed to scroll
      // Zero opacity animation, zero gradient overlays - crisp boundary at all scroll offsets
      gsap.fromTo(
        sheet,
        { yPercent: 25 },
        {
          yPercent: 0,
          ease: "none",
          scrollTrigger: {
            trigger: container,
            start: "top bottom",
            end: "top 25%",
            scrub: true,
            onUpdate: (self) => {
              if (self.progress >= 0.5) {
                document.body.setAttribute("data-active-theme", to);
              } else {
                document.body.setAttribute("data-active-theme", from);
              }
            },
          },
        }
      );
    }, container);

    return () => ctx.revert();
  }, [from, to, reducedMotion]);

  const sheetBg =
    to === "light"
      ? "bg-[#FAFAFA] text-[#0A0A0A]"
      : "bg-[#050505] text-[#FFFFFF]";

  return (
    <div
      ref={containerRef}
      id={id}
      className={cn("relative w-full overflow-hidden scroll-mt-[112px]", className)}
      data-theme={to}
    >
      {/* 
        Solid, opaque sheet with 32px rounded top edge.
        At 50% scroll progress: crisp black above, crisp near-white below.
      */}
      <div
        ref={sheetRef}
        className={cn(
          "relative z-10 w-full rounded-t-[32px] overflow-hidden will-change-transform",
          sheetBg
        )}
      >
        {children}
      </div>
    </div>
  );
}
