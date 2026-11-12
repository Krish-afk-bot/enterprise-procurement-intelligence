import { useEffect, useRef } from "react";

/**
 * Animated particles that flow along an SVG path.
 *
 * Used to visualize data flow in the evidence chain. Particles travel from
 * start to end of the path, with staggered timing for a continuous stream effect.
 */
interface FlowParticle {
  id: number;
  progress: number;
  speed: number;
  delay: number;
}

export function FlowParticles({
  pathRef,
  active = false,
  particleCount = 6,
  className = "",
}: {
  pathRef: React.RefObject<SVGPathElement>;
  active?: boolean;
  particleCount?: number;
  className?: string;
}) {
  const particlesRef = useRef<FlowParticle[]>([]);
  const frameRef = useRef<number>(0);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const path = pathRef.current;
    const svg = svgRef.current;
    if (!path || !svg || !active) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;

    // Initialize particles with staggered delays
    const particles: FlowParticle[] = [];
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        id: i,
        progress: (i / particleCount) * 100,
        speed: 0.15 + Math.random() * 0.1,
        delay: 0,
      });
    }
    particlesRef.current = particles;

    const pathLength = path.getTotalLength();

    const animate = () => {
      particles.forEach((particle) => {
        particle.progress += particle.speed;
        if (particle.progress > 100) {
          particle.progress = 0;
        }

        // Get position on path
        const distance = (particle.progress / 100) * pathLength;
        const point = path.getPointAtLength(distance);

        // Find corresponding circle element
        const circle = svg.querySelector(`[data-particle-id="${particle.id}"]`) as SVGCircleElement;
        if (circle) {
          circle.setAttribute("cx", String(point.x));
          circle.setAttribute("cy", String(point.y));
          // Fade in/out at edges
          const opacity = particle.progress < 10
            ? particle.progress / 10
            : particle.progress > 90
              ? (100 - particle.progress) / 10
              : 1;
          circle.setAttribute("opacity", String(opacity * 0.7));
        }
      });

      frameRef.current = window.requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (frameRef.current) window.cancelAnimationFrame(frameRef.current);
    };
  }, [pathRef, active, particleCount]);

  if (!active) return null;

  return (
    <svg
      ref={svgRef}
      className={`pointer-events-none absolute motion-reduce:hidden ${className}`}
      viewBox="0 0 64 64"
      aria-hidden="true"
    >
      {Array.from({ length: particleCount }).map((_, index) => (
        <circle
          key={index}
          data-particle-id={index}
          r="1.5"
          fill="white"
          opacity="0"
        />
      ))}
    </svg>
  );
}
