import { useEffect, useRef } from "react";

/**
 * Animated procurement data network — flowing data points representing
 * document ingestion, query routing, and relationship resolution.
 *
 * Pure CSS + RAF animation, no heavy dependencies. Shows activity without
 * making specific procurement claims. Hidden for reduced motion.
 */

interface DataPoint {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
  type: "document" | "query" | "relationship";
}

const COLORS = {
  document: "rgba(255, 255, 255, 0.6)",
  query: "rgba(255, 255, 255, 0.45)",
  relationship: "rgba(255, 255, 255, 0.3)",
};

export function AnimatedDataPoints() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pointsRef = useRef<DataPoint[]>([]);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Setup canvas size
    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
    };

    resize();
    window.addEventListener("resize", resize);

    // Initialize data points
    const types: DataPoint["type"][] = ["document", "query", "relationship"];
    const points: DataPoint[] = [];

    for (let i = 0; i < 24; i++) {
      points.push({
        id: `point-${i}`,
        x: Math.random() * canvas.offsetWidth,
        y: Math.random() * canvas.offsetHeight,
        vx: (Math.random() - 0.5) * 0.15,
        vy: (Math.random() - 0.5) * 0.15,
        size: Math.random() * 2 + 1,
        opacity: Math.random() * 0.4 + 0.2,
        type: types[Math.floor(Math.random() * types.length)],
      });
    }

    pointsRef.current = points;

    // Animation loop
    const animate = () => {
      ctx.clearRect(0, 0, canvas.offsetWidth, canvas.offsetHeight);

      // Update and draw points
      points.forEach((point) => {
        point.x += point.vx;
        point.y += point.vy;

        // Wrap around edges
        if (point.x < 0) point.x = canvas.offsetWidth;
        if (point.x > canvas.offsetWidth) point.x = 0;
        if (point.y < 0) point.y = canvas.offsetHeight;
        if (point.y > canvas.offsetHeight) point.y = 0;

        // Draw point
        ctx.fillStyle = COLORS[point.type];
        ctx.globalAlpha = point.opacity;
        ctx.beginPath();
        ctx.arc(point.x, point.y, point.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // Draw connections between nearby points
      ctx.globalAlpha = 0.1;
      for (let i = 0; i < points.length; i++) {
        for (let j = i + 1; j < points.length; j++) {
          const p1 = points[i];
          const p2 = points[j];
          const dx = p2.x - p1.x;
          const dy = p2.y - p1.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 120) {
            const opacity = (1 - dist / 120) * 0.12;
            ctx.strokeStyle = `rgba(255, 255, 255, ${opacity})`;
            ctx.lineWidth = 0.5;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }
      }

      ctx.globalAlpha = 1;
      frameRef.current = window.requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener("resize", resize);
      if (frameRef.current) window.cancelAnimationFrame(frameRef.current);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 opacity-40 motion-reduce:hidden"
      aria-hidden="true"
    />
  );
}
