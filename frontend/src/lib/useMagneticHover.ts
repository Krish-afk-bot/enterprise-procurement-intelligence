import { useEffect, useRef } from "react";

/**
 * Magnetic hover — the element subtly follows the pointer when nearby.
 *
 * Returns a ref to attach to the interactive element. The effect is desktop-only,
 * fine-pointer-only, and off for reduced motion. On touch or when motion is
 * reduced the element behaves normally.
 *
 * @param strength — How far the element moves (0–1, default 0.3)
 * @param radius — How far from the element the effect activates (px, default 80)
 */
export function useMagneticHover<T extends HTMLElement>(
  strength = 0.3,
  radius = 80,
) {
  const ref = useRef<T>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fine || reduce) return;

    let frame = 0;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const lerp = (start: number, end: number, factor: number) =>
      start + (end - start) * factor;

    const update = () => {
      currentX = lerp(currentX, targetX, 0.15);
      currentY = lerp(currentY, targetY, 0.15);
      node.style.transform = `translate3d(${currentX.toFixed(1)}px, ${currentY.toFixed(1)}px, 0)`;

      if (Math.abs(currentX - targetX) > 0.1 || Math.abs(currentY - targetY) > 0.1) {
        frame = window.requestAnimationFrame(update);
      } else {
        frame = 0;
      }
    };

    const onMove = (event: PointerEvent) => {
      const rect = node.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const distX = event.clientX - centerX;
      const distY = event.clientY - centerY;
      const distance = Math.sqrt(distX * distX + distY * distY);

      if (distance < radius) {
        const force = (radius - distance) / radius;
        targetX = (distX / radius) * strength * force * 20;
        targetY = (distY / radius) * strength * force * 20;
      } else {
        targetX = 0;
        targetY = 0;
      }

      if (!frame) frame = window.requestAnimationFrame(update);
    };

    const onLeave = () => {
      targetX = 0;
      targetY = 0;
      if (!frame) frame = window.requestAnimationFrame(update);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    node.addEventListener("pointerleave", onLeave);

    return () => {
      window.removeEventListener("pointermove", onMove);
      node.removeEventListener("pointerleave", onLeave);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [strength, radius]);

  return ref;
}
