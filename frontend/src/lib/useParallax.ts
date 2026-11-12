import { useEffect, useRef } from "react";

/**
 * Generalized parallax effect — element moves in response to scroll or pointer.
 *
 * @param mode — "scroll" moves based on viewport scroll, "pointer" follows cursor
 * @param strength — How much to move (0–1, default 0.5 for scroll, 0.3 for pointer)
 * @param axis — "y" (vertical), "x" (horizontal), or "both"
 */
export function useParallax<T extends HTMLElement>(
  mode: "scroll" | "pointer" = "scroll",
  strength = mode === "scroll" ? 0.5 : 0.3,
  axis: "x" | "y" | "both" = mode === "scroll" ? "y" : "both",
) {
  const ref = useRef<T>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;

    if (mode === "scroll") {
      return setupScrollParallax(node, strength, axis);
    } else {
      return setupPointerParallax(node, strength, axis);
    }
  }, [mode, strength, axis]);

  return ref;
}

function setupScrollParallax(
  node: HTMLElement,
  strength: number,
  axis: "x" | "y" | "both",
) {
  let ticking = false;

  const update = () => {
    const rect = node.getBoundingClientRect();
    const centerY = rect.top + rect.height / 2;
    const viewportCenter = window.innerHeight / 2;
    const offset = (centerY - viewportCenter) * strength * -0.1;

    if (axis === "y") {
      node.style.transform = `translateY(${offset.toFixed(1)}px)`;
    } else if (axis === "x") {
      node.style.transform = `translateX(${offset.toFixed(1)}px)`;
    } else {
      node.style.transform = `translate(${(offset * 0.5).toFixed(1)}px, ${offset.toFixed(1)}px)`;
    }
    ticking = false;
  };

  const onScroll = () => {
    if (!ticking) {
      window.requestAnimationFrame(update);
      ticking = true;
    }
  };

  update();
  window.addEventListener("scroll", onScroll, { passive: true });
  return () => window.removeEventListener("scroll", onScroll);
}

function setupPointerParallax(
  node: HTMLElement,
  strength: number,
  axis: "x" | "y" | "both",
) {
  const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  if (!fine) return;

  let frame = 0;

  const onMove = (event: PointerEvent) => {
    const xOffset = (event.clientX / window.innerWidth - 0.5) * strength * -20;
    const yOffset = (event.clientY / window.innerHeight - 0.5) * strength * -20;

    if (frame) window.cancelAnimationFrame(frame);
    frame = window.requestAnimationFrame(() => {
      if (axis === "y") {
        node.style.transform = `translateY(${yOffset.toFixed(1)}px)`;
      } else if (axis === "x") {
        node.style.transform = `translateX(${xOffset.toFixed(1)}px)`;
      } else {
        node.style.transform = `translate(${xOffset.toFixed(1)}px, ${yOffset.toFixed(1)}px)`;
      }
      frame = 0;
    });
  };

  window.addEventListener("pointermove", onMove, { passive: true });
  return () => {
    window.removeEventListener("pointermove", onMove);
    if (frame) window.cancelAnimationFrame(frame);
  };
}
