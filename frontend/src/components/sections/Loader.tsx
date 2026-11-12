import { useEffect, useRef, useState } from "react";
import { loadScroll, motionAllowed } from "@/components/motion/scroll";
import { Logo } from "@/components/brand/Logo";

interface LoaderProps {
  onComplete: () => void;
}

/**
 * Animated loader sequence (Scene 00).
 *
 * Ring → Brand mark → Curtain reveal
 *
 * Runs once on first visit (uses sessionStorage), skips on reduced motion.
 * Does not block page if animation fails.
 */
export function Loader({ onComplete }: LoaderProps) {
  const [visible, setVisible] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Skip loader if:
    // 1. Already seen this session
    // 2. Reduced motion preference
    // 3. Not first visit
    const hasSeenLoader = sessionStorage.getItem("epi-loader-seen");
    if (hasSeenLoader || !motionAllowed()) {
      onComplete();
      setVisible(false);
      return;
    }

    sessionStorage.setItem("epi-loader-seen", "true");

    const container = containerRef.current;
    if (!container) {
      onComplete();
      setVisible(false);
      return;
    }

    let cancelled = false;
    let context: { revert: () => void } | undefined;

    void loadScroll()
      .then(({ gsap }) => {
        if (cancelled || !container) {
          onComplete();
          setVisible(false);
          return;
        }

        const ring = container.querySelector(".loader-ring") as HTMLElement;
        const logo = container.querySelector(".loader-logo") as HTMLElement;
        const curtain = container.querySelector(".loader-curtain") as HTMLElement;

        if (!ring || !logo || !curtain) {
          onComplete();
          setVisible(false);
          return;
        }

        // Timeline
        context = gsap.context(() => {
          const tl = gsap.timeline({
            onComplete: () => {
              setVisible(false);
              onComplete();
            },
          });

          // 1. Ring appears and pulses
          tl.fromTo(
            ring,
            { scale: 0.8, opacity: 0 },
            { scale: 1, opacity: 1, duration: 0.4, ease: "cubic-bezier(0.22, 1, 0.36, 1)" }
          )
            .to(ring, {
              scale: 1.1,
              opacity: 0.8,
              duration: 0.6,
              ease: "sine.inOut",
              repeat: 1,
              yoyo: true,
            })
            // 2. Ring fades out
            .to(ring, {
              opacity: 0,
              scale: 0.9,
              duration: 0.3,
            })
            // 3. Logo morphs in
            .fromTo(
              logo,
              { scale: 0.5, opacity: 0 },
              { scale: 1, opacity: 1, duration: 0.5, ease: "cubic-bezier(0.22, 1, 0.36, 1)" },
              "-=0.1"
            )
            // 4. Logo scales up slightly
            .to(logo, {
              scale: 1.05,
              duration: 0.3,
            })
            // 5. Curtain rises
            .to(
              curtain,
              {
                yPercent: -100,
                duration: 0.8,
                ease: "cubic-bezier(0.22, 1, 0.36, 1)",
              },
              "-=0.2"
            );
        }, container);
      })
      .catch(() => {
        // If GSAP fails to load, don't block the page
        onComplete();
        setVisible(false);
      });

    return () => {
      cancelled = true;
      context?.revert();
    };
  }, [onComplete]);

  if (!visible) return null;

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-3"
      aria-live="polite"
      aria-label="Loading"
    >
      {/* Ring */}
      <div className="loader-ring absolute h-16 w-16 rounded-full border-2 border-white/20">
        <div className="absolute left-1/2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white" />
      </div>

      {/* Logo */}
      <div className="loader-logo absolute opacity-0">
        <Logo />
      </div>

      {/* Black curtain that rises */}
      <div className="loader-curtain pointer-events-none absolute inset-0 bg-ink" />
    </div>
  );
}
