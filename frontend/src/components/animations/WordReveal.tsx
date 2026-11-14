import { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { cn } from "@/lib/utils";
import { useMotionMode } from "@/motion/motion";

gsap.registerPlugin(ScrollTrigger);

interface WordRevealProps {
  children: string;
  as?: "h1" | "h2" | "h3" | "h4" | "p" | "span";
  mode?: "scroll" | "time";
  delay?: number;
  className?: string;
  wordClassName?: string;
}

export function WordReveal({
  children,
  as: Component = "h2",
  mode = "scroll",
  delay = 0,
  className,
  wordClassName,
}: WordRevealProps) {
  const containerRef = useRef<HTMLElement>(null);
  const motionMode = useMotionMode();

  const words = children.split(/\s+/).filter(Boolean);

  useLayoutEffect(() => {
    if (motionMode === "off" || !containerRef.current) return;

    const el = containerRef.current;
    const wordSpans = el.querySelectorAll<HTMLElement>(".word-span-inner");

    const ctx = gsap.context(() => {
      const full = motionMode === "full";

      if (mode === "time") {
        gsap.fromTo(
          wordSpans,
          {
            opacity: 0.15,
            y: full ? 24 : 0,
            filter: full ? "blur(6px)" : "none",
            color: "rgba(255, 255, 255, 0.3)",
          },
          {
            opacity: 1,
            y: 0,
            filter: "none",
            color: "inherit",
            duration: 0.85,
            stagger: 0.08,
            ease: "power3.out",
            delay,
            onComplete: () => {
              // F6.1: Remove overflow mask so descenders are never clipped
              el.querySelectorAll<HTMLElement>(".word-mask").forEach((mask) => {
                mask.style.overflow = "visible";
              });
            },
          }
        );
      } else {
        // Scroll scrub mode
        gsap.fromTo(
          wordSpans,
          {
            opacity: 0.15,
            y: full ? 20 : 0,
            filter: full ? "blur(5px)" : "none",
          },
          {
            opacity: 1,
            y: 0,
            filter: "none",
            stagger: 0.08,
            ease: "power2.out",
            scrollTrigger: {
              trigger: el,
              start: "top 85%",
              end: "top 45%",
              scrub: 0.8,
            },
            onComplete: () => {
              el.querySelectorAll<HTMLElement>(".word-mask").forEach((mask) => {
                mask.style.overflow = "visible";
              });
            },
          }
        );
      }
    }, el);

    return () => ctx.revert();
  }, [motionMode, mode, delay]);

  if (motionMode === "off") {
    return <Component className={cn("leading-[1.12]", className)}>{children}</Component>;
  }

  return (
    <Component
      ref={containerRef as any}
      className={cn("inline-block leading-[1.12]", className)}
      aria-label={children}
    >
      {words.map((word, idx) => (
        <span
          key={`${word}-${idx}`}
          className="word-mask inline-block overflow-hidden pb-[0.18em] -mb-[0.18em] mr-[0.26em] last:mr-0 align-top"
          aria-hidden="true"
        >
          <span
            className={cn(
              "word-span-inner inline-block transform-gpu will-change-transform will-change-opacity",
              wordClassName
            )}
          >
            {word}
          </span>
        </span>
      ))}
    </Component>
  );
}
