import { useEffect } from "react";

import type { WorldMood } from "@/content/microcopy";
import { useWorld } from "@/store/world";

/**
 * Tells the world what the application is actually doing.
 *
 * This is the only bridge between real state and the decorative layer: the hook
 * is called from components that already know the truth (an answer is running,
 * the results came back empty, a request failed) and never from a timer. When
 * the component goes away the world goes back to idle, provided nobody else has
 * reported a newer state in the meantime.
 *
 * Passing `null` means "this component has nothing to say right now".
 */
export function useMood(mood: WorldMood | null): void {
  useEffect(() => {
    if (!mood) return;
    const store = useWorld.getState();
    store.setMood(mood);
    return () => {
      const current = useWorld.getState();
      if (current.mood === mood) current.setMood("idle");
    };
  }, [mood]);
}
