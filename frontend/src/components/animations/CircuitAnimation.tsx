import { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { cn } from "@/lib/utils";

interface CircuitAnimationProps {
  className?: string;
}

export function CircuitAnimation({ className }: CircuitAnimationProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const reducedMotion = useReducedMotion();

  useLayoutEffect(() => {
    if (reducedMotion || !svgRef.current) return;

    const svg = svgRef.current;
    const paths = svg.querySelectorAll<SVGPathElement>(".circuit-trace");
    const pulses = svg.querySelectorAll<SVGCircleElement>(".circuit-pulse");

    const ctx = gsap.context(() => {
      // Draw traces
      paths.forEach((path) => {
        const length = path.getTotalLength();
        gsap.set(path, {
          strokeDasharray: length,
          strokeDashoffset: length,
        });

        gsap.to(path, {
          strokeDashoffset: 0,
          duration: 2.2,
          ease: "power2.inOut",
          delay: 0.3,
        });
      });

      // Animate pulses looping along circuit paths
      pulses.forEach((pulse, i) => {
        gsap.to(pulse, {
          opacity: 0.8,
          scale: 1.4,
          duration: 1.8,
          repeat: -1,
          yoyo: true,
          ease: "sine.inOut",
          delay: i * 0.4,
        });
      });
    }, svg);

    return () => ctx.revert();
  }, [reducedMotion]);

  return (
    <div className={cn("relative pointer-events-none select-none", className)}>
      <svg
        ref={svgRef}
        viewBox="0 0 1000 480"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full opacity-70"
      >
        <defs>
          <linearGradient id="traceGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FF4D00" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#FF7A1A" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0.05" />
          </linearGradient>
          <radialGradient id="pulseGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#FF7A1A" stopOpacity="1" />
            <stop offset="100%" stopColor="#FF4D00" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Center engine hub */}
        <circle cx="500" cy="240" r="32" stroke="rgba(255, 77, 0, 0.4)" strokeWidth="1.5" />
        <circle cx="500" cy="240" r="16" fill="rgba(255, 77, 0, 0.15)" stroke="#FF4D00" strokeWidth="1.5" />

        {/* Left circuit branches */}
        <path
          className="circuit-trace"
          d="M 468 240 L 320 240 L 260 160 L 140 160"
          stroke="url(#traceGrad)"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <path
          className="circuit-trace"
          d="M 470 250 L 340 310 L 210 310 L 160 380"
          stroke="url(#traceGrad)"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <path
          className="circuit-trace"
          d="M 480 220 L 390 130 L 280 130"
          stroke="url(#traceGrad)"
          strokeWidth="1.5"
          strokeLinecap="round"
        />

        {/* Right circuit branches */}
        <path
          className="circuit-trace"
          d="M 532 240 L 680 240 L 740 160 L 860 160"
          stroke="url(#traceGrad)"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <path
          className="circuit-trace"
          d="M 530 250 L 660 310 L 790 310 L 840 380"
          stroke="url(#traceGrad)"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <path
          className="circuit-trace"
          d="M 520 220 L 610 130 L 720 130"
          stroke="url(#traceGrad)"
          strokeWidth="1.5"
          strokeLinecap="round"
        />

        {/* Termination nodes */}
        <circle cx="140" cy="160" r="5" fill="#FF4D00" className="circuit-pulse" />
        <circle cx="160" cy="380" r="5" fill="#FF7A1A" className="circuit-pulse" />
        <circle cx="280" cy="130" r="4" fill="#FF4D00" className="circuit-pulse" />
        <circle cx="860" cy="160" r="5" fill="#FF4D00" className="circuit-pulse" />
        <circle cx="840" cy="380" r="5" fill="#FF7A1A" className="circuit-pulse" />
        <circle cx="720" cy="130" r="4" fill="#FF4D00" className="circuit-pulse" />
      </svg>
    </div>
  );
}
