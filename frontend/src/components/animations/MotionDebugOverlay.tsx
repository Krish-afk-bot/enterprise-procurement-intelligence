import { useEffect, useState } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { getEffectiveMotionMode, useMotionMode } from "@/motion/motion";

export function MotionDebugOverlay() {
  const [visible, setVisible] = useState(false);
  const [stats, setStats] = useState({
    mode: "full",
    osReduced: false,
    gsapVersion: gsap.version,
    activeTweens: 0,
    scrollTriggers: 0,
    fps: 60,
  });
  const mode = useMotionMode();

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("motion") === "debug") {
      setVisible(true);
    }
  }, []);

  useEffect(() => {
    if (!visible) return;

    let frames = 0;
    let prevTime = performance.now();
    let currentFps = 60;

    const interval = setInterval(() => {
      const now = performance.now();
      currentFps = Math.round((frames * 1000) / (now - prevTime));
      frames = 0;
      prevTime = now;

      setStats({
        mode: getEffectiveMotionMode(),
        osReduced: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
        gsapVersion: gsap.version,
        activeTweens: gsap.globalTimeline.getChildren(true, true, true).length,
        scrollTriggers: ScrollTrigger.getAll().length,
        fps: currentFps || 60,
      });
    }, 500);

    let rafId: number;
    const countFrames = () => {
      frames++;
      rafId = requestAnimationFrame(countFrames);
    };
    rafId = requestAnimationFrame(countFrames);

    return () => {
      clearInterval(interval);
      cancelAnimationFrame(rafId);
    };
  }, [visible, mode]);

  if (!visible) return null;

  return (
    <div
      id="motion-debug-overlay"
      className="fixed bottom-4 right-4 z-[9999] p-3.5 rounded-2xl bg-black/90 border border-[#FF4D00]/50 text-white font-mono text-[11px] shadow-2xl backdrop-blur-md flex flex-col gap-1.5 pointer-events-none"
    >
      <div className="flex items-center justify-between gap-4 font-bold text-[#FF4D00]">
        <span>MOTION DEBUG</span>
        <span>{stats.fps} FPS</span>
      </div>
      <div className="flex justify-between gap-4">
        <span className="text-white/60">Effective Mode:</span>
        <span className="font-semibold text-emerald-400">{stats.mode}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span className="text-white/60">OS Reduced Motion:</span>
        <span>{stats.osReduced ? "true (reduce)" : "false (no-pref)"}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span className="text-white/60">Active Tweens:</span>
        <span>{stats.activeTweens}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span className="text-white/60">ScrollTriggers:</span>
        <span>{stats.scrollTriggers}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span className="text-white/60">GSAP:</span>
        <span>v{stats.gsapVersion}</span>
      </div>
    </div>
  );
}

