import { useEffect, useState } from "react";
import { gsap } from "gsap";
import { useReducedMotion } from "@/hooks/useReducedMotion";

interface LoaderProps {
  onComplete: () => void;
}

export function Loader({ onComplete }: LoaderProps) {
  const [active, setActive] = useState(true);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    // Check if already viewed in this session
    const hasSeenLoader = sessionStorage.getItem("epi_loader_seen");
    if (hasSeenLoader || reducedMotion) {
      setActive(false);
      onComplete();
      return;
    }

    const ring = document.getElementById("loader-ring");
    const dot = document.getElementById("loader-dot");
    const brand = document.getElementById("loader-brand");
    const curtain = document.getElementById("loader-curtain");

    const tl = gsap.timeline({
      onComplete: () => {
        sessionStorage.setItem("epi_loader_seen", "true");
        setActive(false);
        onComplete();
      },
    });

    // Ring + dot pulse
    tl.fromTo(
      dot,
      { scale: 0.6, opacity: 0.4 },
      { scale: 1, opacity: 1, duration: 0.6, ease: "power2.out" }
    )
      .fromTo(
        ring,
        { scale: 0.8, opacity: 0 },
        { scale: 1.2, opacity: 0.8, duration: 0.7, ease: "power2.out" },
        "-=0.4"
      )
      // Morph/crossfade into brand wordmark
      .to([ring, dot], { opacity: 0, scale: 1.4, duration: 0.4 })
      .fromTo(
        brand,
        { opacity: 0, scale: 0.9, y: 10 },
        { opacity: 1, scale: 1, y: 0, duration: 0.6, ease: "power3.out" },
        "-=0.2"
      )
      // Curtain wipe upward
      .to(curtain, {
        yPercent: -100,
        duration: 0.9,
        ease: "power3.inOut",
        delay: 0.3,
      });

    return () => {
      tl.kill();
    };
  }, [reducedMotion, onComplete]);

  if (!active) return null;

  return (
    <div
      id="loader-curtain"
      className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-[#141414] text-white select-none pointer-events-auto transform-gpu will-change-transform"
    >
      {/* Centered pulse container */}
      <div className="relative flex flex-col items-center justify-center w-64 h-64">
        {/* Outer glowing ring */}
        <div
          id="loader-ring"
          className="absolute w-24 h-24 rounded-full border border-[#FF4D00]/50 shadow-[0_0_40px_rgba(255,77,0,0.3)]"
        />

        {/* Inner pulsing core dot */}
        <div
          id="loader-dot"
          className="w-4 h-4 rounded-full bg-[#FF4D00] shadow-[0_0_20px_#FF7A1A]"
        />

        {/* Brand wordmark reveal */}
        <div
          id="loader-brand"
          className="absolute flex flex-col items-center opacity-0"
        >
          <div className="w-12 h-12 rounded-2xl bg-[#FF4D00] flex items-center justify-center text-white font-bold text-2xl shadow-xl shadow-[#FF4D00]/40 mb-3">
            E
          </div>
          <span className="text-xl font-bold tracking-tight text-white">EPI</span>
          <span className="text-[10px] uppercase tracking-widest text-white/50 mt-1">
            Enterprise Procurement Intelligence
          </span>
        </div>
      </div>

      {/* Subtle bottom progress marker */}
      <div className="absolute bottom-10 text-xs text-white/40 tracking-wider font-mono">
        INITIALIZING REASONING ENGINE
      </div>
    </div>
  );
}
