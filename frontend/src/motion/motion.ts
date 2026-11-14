import { useSyncExternalStore } from "react";

export type MotionPref = "system" | "full" | "reduced" | "off";
export type MotionMode = "full" | "reduced" | "off";

const STORAGE_KEY = "epi-motion";
const mq = typeof window !== "undefined" ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
const subscribers = new Set<() => void>();

const readPref = (): MotionPref => {
  try {
    return (localStorage.getItem(STORAGE_KEY) as MotionPref) || "system";
  } catch {
    return "system";
  }
};

export const getEffectiveMotionMode = (): MotionMode => {
  const pref = readPref();
  if (pref === "full") return "full";
  if (pref === "reduced") return "reduced";
  if (pref === "off") return "off";
  return mq?.matches ? "reduced" : "full";
};

export const setMotionPref = (pref: MotionPref) => {
  try {
    localStorage.setItem(STORAGE_KEY, pref);
  } catch {}
  applyMotionToDoc();
  subscribers.forEach((fn) => fn());
};

const applyMotionToDoc = () => {
  if (typeof document !== "undefined") {
    document.documentElement.dataset.motion = getEffectiveMotionMode();
  }
};

if (typeof window !== "undefined") {
  mq?.addEventListener("change", () => {
    applyMotionToDoc();
    subscribers.forEach((fn) => fn());
  });
  applyMotionToDoc();
}

export const useMotionMode = (): MotionMode => {
  return useSyncExternalStore(
    (callback) => {
      subscribers.add(callback);
      return () => subscribers.delete(callback);
    },
    getEffectiveMotionMode,
    () => "full" as MotionMode
  );
};

