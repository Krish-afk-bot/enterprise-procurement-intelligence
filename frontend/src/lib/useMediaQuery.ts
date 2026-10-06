import { useEffect, useState } from "react";

/**
 * Screen-size decisions for the 3D surfaces. A tablet gets a lighter scene and
 * a phone gets the written alternative instead of a WebGL canvas, so a small
 * device is never asked to run the full scene.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window === "undefined" ? false : window.matchMedia(query).matches,
  );

  useEffect(() => {
    const list = window.matchMedia(query);
    const onChange = (event: MediaQueryListEvent) => setMatches(event.matches);
    setMatches(list.matches);
    list.addEventListener("change", onChange);
    return () => list.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}

/** Phones and other small screens: the scene is replaced by its text version. */
export function useSmallScreen(): boolean {
  return useMediaQuery("(max-width: 767px)");
}

/** Tablets: the scene runs, with fewer particles and shorter geometry. */
export function useReducedDetail(): boolean {
  return useMediaQuery("(max-width: 1279px)");
}

/** True when the browser cannot create a WebGL context at all. */
export function hasWebGL(): boolean {
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      canvas.getContext("webgl2") ??
        canvas.getContext("webgl") ??
        canvas.getContext("experimental-webgl" as "webgl"),
    );
  } catch {
    return false;
  }
}
