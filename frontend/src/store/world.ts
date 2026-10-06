import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { WorldMood } from "@/content/microcopy";

/**
 * What the device can afford. Chosen from real signals, downgraded on bad frames.
 * `static` is the last step: the canvas is dropped and the written/SVG layer is
 * shown instead, so a machine that cannot hold the budget still gets the world.
 */
export type QualityTier = "high" | "medium" | "low" | "static";

interface WorldState {
  // -------------------------------------------------------------- user settings
  /** "Reduce effects" — fewer moving things, no shadows, lower pixel ratio. */
  reduceEffects: boolean;
  /** "Hide buddy" — the decorative characters are not rendered at all. */
  hideBuddy: boolean;
  setReduceEffects: (value: boolean) => void;
  setHideBuddy: (value: boolean) => void;

  // ------------------------------------------------------------------ live state
  /**
   * The mood the world expresses. It is set from real application state — a query
   * running, a conflict found, a refusal — and never from a timer.
   */
  mood: WorldMood;
  /**
   * When the mood was set, on the frame clock (`performance.now()`), which is
   * the clock the Watcher reads while it draws. Stamping this with `Date.now()`
   * would hand the scene an epoch timestamp to subtract from a page-relative
   * one: an age of roughly minus fifty years, and a face scaled into the sky.
   */
  moodAt: number;
  setMood: (mood: WorldMood) => void;

  /** Frame-time downgrade, written by the canvas when frames get expensive. */
  quality: QualityTier;
  setQuality: (tier: QualityTier) => void;

  /** A line the Watcher is showing after being clicked; cleared shortly after. */
  buddyLine: string | null;
  setBuddyLine: (line: string | null) => void;

  /**
   * Incremented when the Watcher is clicked. The scene reads the counter rather
   * than subscribing to React, so a click costs one re-render of the band and
   * nothing else.
   */
  poke: number;
  pokeAt: number;
  pokeWatcher: () => void;
}

export const useWorld = create<WorldState>()(
  persist(
    (set) => ({
      reduceEffects: false,
      hideBuddy: false,
      setReduceEffects: (value) => set({ reduceEffects: value }),
      setHideBuddy: (value) => set({ hideBuddy: value }),

      mood: "idle",
      moodAt: 0,
      setMood: (mood) => set({ mood, moodAt: typeof performance === "undefined" ? 0 : performance.now() }),

      quality: "high",
      setQuality: (tier) => set({ quality: tier }),

      buddyLine: null,
      setBuddyLine: (line) => set({ buddyLine: line }),

      poke: 0,
      pokeAt: 0,
      pokeWatcher: () => set((state) => ({ poke: state.poke + 1, pokeAt: Date.now() })),
    }),
    {
      name: "epi-world",
      // Only the reader's choices are persisted. Mood, quality and the current
      // line are runtime state and must not survive a reload.
      partialize: (state) => ({ reduceEffects: state.reduceEffects, hideBuddy: state.hideBuddy }),
    },
  ),
);
