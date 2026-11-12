import { useEffect, useRef } from "react";
import { loadScroll, motionAllowed } from "@/components/motion/scroll";

interface CircuitPath {
  id: string;
  d: string; // SVG path data
  length?: number; // Auto-calculated if not provided
}

interface CircuitAnimationProps {
  paths: CircuitPath[];
  /** Draw duration in seconds */
  drawDuration?: number;
  /** Delay before starting in seconds */
  delay?: number;
  /** Stagger between paths in seconds */
  stagger?: number;
  /** Show pulse particles after drawing */
  showPulses?: boolean;
  /** Pulse duration in seconds */
  pulseDuration?: number;
  className?: string;
  viewBox?: string;
}

/**
 * Animated circuit paths with drawing effect and optional pulses.
 *
 * Paths are drawn using stroke-dasharray and stroke-dashoffset animation,
 * then small orange pulses travel along the paths continuously.
 */
export function CircuitAnimation({
  paths,
  drawDuration = 1.2,
  delay = 0,
  stagger = 0.1,
  showPulses = true,
  pulseDuration = 3,
  className = "",
  viewBox = "0 0 800 600",
}: CircuitAnimationProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!motionAllowed()) return;

    const svg = svgRef.current;
    if (!svg) return;

    let cancelled = false;
    let context: { revert: () => void } | undefined;

    void loadScroll().then(({ gsap }) => {
      if (cancelled || !svg) return;

      // Get all path elements
      const pathElements = svg.querySelectorAll(".circuit-path");

      if (pathElements.length === 0) return;

      context = gsap.context(() => {
        // Set up path drawing
        pathElements.forEach((path) => {
          const pathElement = path as SVGPathElement;
          const length = pathElement.getTotalLength();

          gsap.set(pathElement, {
            strokeDasharray: length,
            strokeDashoffset: length,
          });
        });

        // Animate drawing
        gsap.to(pathElements, {
          strokeDashoffset: 0,
          duration: drawDuration,
          delay,
          stagger,
          ease: "cubic-bezier(0.22, 1, 0.36, 1)",
        });

        // Animate pulses if enabled
        if (showPulses) {
          const pulses = svg.querySelectorAll(".circuit-pulse");
          if (pulses.length > 0) {
            gsap.set(pulses, { opacity: 0 });

            // Start pulses after paths are drawn
            gsap.to(pulses, {
              opacity: 1,
              delay: delay + drawDuration + 0.3,
              duration: 0.3,
            });

            // Animate each pulse along its path
            pulses.forEach((pulse, index) => {
              const pathId = pulse.getAttribute("data-path-id");
              const pathElement = svg.querySelector(`#${pathId}`) as SVGPathElement;

              if (!pathElement) return;

              gsap.to(pulse, {
                motionPath: {
                  path: pathElement,
                  align: pathElement,
                  alignOrigin: [0.5, 0.5],
                },
                duration: pulseDuration,
                delay: delay + drawDuration + 0.5 + index * 0.5,
                ease: "none",
                repeat: -1,
                repeatDelay: 1,
              });
            });
          }
        }
      }, svg);
    });

    return () => {
      cancelled = true;
      context?.revert();
    };
  }, [paths, drawDuration, delay, stagger, showPulses, pulseDuration]);

  return (
    <svg ref={svgRef} viewBox={viewBox} className={`h-full w-full ${className}`} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="pulse-gradient">
          <stop offset="0%" stopColor="#FB923C" stopOpacity="1" />
          <stop offset="100%" stopColor="#FB923C" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Circuit paths */}
      <g className="circuit-paths">
        {paths.map((path) => (
          <path
            key={path.id}
            id={path.id}
            d={path.d}
            className="circuit-path"
            stroke="rgba(251, 146, 60, 0.6)"
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}
      </g>

      {/* Pulse particles */}
      {showPulses && (
        <g className="circuit-pulses">
          {paths.map((path) => (
            <circle
              key={`pulse-${path.id}`}
              className="circuit-pulse"
              data-path-id={path.id}
              r="4"
              fill="url(#pulse-gradient)"
            />
          ))}
        </g>
      )}
    </svg>
  );
}

/**
 * Helper to create circuit paths for chip visualization.
 * Returns common path patterns for hero circuit.
 */
export function createChipPaths(centerX: number, centerY: number, radius: number): CircuitPath[] {
  const paths: CircuitPath[] = [];
  const angles = [0, 60, 120, 180, 240, 300]; // 6 directions

  angles.forEach((angle, index) => {
    const rad = (angle * Math.PI) / 180;
    const x1 = centerX + radius * Math.cos(rad);
    const y1 = centerY + radius * Math.sin(rad);
    const x2 = centerX + (radius + 100) * Math.cos(rad);
    const y2 = centerY + (radius + 100) * Math.sin(rad);

    paths.push({
      id: `chip-path-${index}`,
      d: `M ${x1},${y1} L ${x2},${y2}`,
    });
  });

  return paths;
}
