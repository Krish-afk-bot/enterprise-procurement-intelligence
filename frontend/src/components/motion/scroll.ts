/**
 * Motion capabilities and the lazy GSAP loader.
 *
 * GSAP is ~70 kB gzipped and only the public landing page uses it, so it is
 * imported on demand instead of being bundled into the entry chunk that every
 * signed-in page also downloads. `loadScroll` caches the promise so four scenes
 * share one network request and one plugin registration.
 */
export function motionAllowed(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: no-preference)").matches
  );
}

/** Pinned sequences are desktop-only; below this they render as a document. */
export const PIN_QUERY = "(min-width: 1024px)";

export const canPin = () =>
  typeof window !== "undefined" && motionAllowed() && window.matchMedia(PIN_QUERY).matches;

type ScrollLib = {
  gsap: typeof import("gsap").gsap;
  ScrollTrigger: typeof import("gsap/ScrollTrigger").ScrollTrigger;
};

let pending: Promise<ScrollLib> | null = null;

export function loadScroll(): Promise<ScrollLib> {
  if (!pending) {
    pending = Promise.all([import("gsap"), import("gsap/ScrollTrigger")]).then(([core, plugin]) => {
      core.gsap.registerPlugin(plugin.ScrollTrigger);
      return { gsap: core.gsap, ScrollTrigger: plugin.ScrollTrigger };
    });
  }
  return pending;
}

/** Recalculate every trigger once late layout (the 3D chunk, fonts) settles. */
export async function refreshScroll(): Promise<void> {
  const { ScrollTrigger } = await loadScroll();
  ScrollTrigger.refresh();
}
