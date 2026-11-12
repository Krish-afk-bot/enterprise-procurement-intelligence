import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { canPin, loadScroll } from "@/components/motion/scroll";
import { WordReveal } from "@/components/animations/WordReveal";
import { Button } from "@/components/ui/button";

/**
 * Sunrise CTA Section (Scene 09).
 *
 * Features:
 * - Full-width card with orange sunrise gradient
 * - Scales into view and gains rounded corners
 * - Deep red → orange → warm white gradient
 * - Memorable visual moment
 */
export function SunriseCTASection() {
  const sectionRef = useRef<HTMLElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);

  // Scroll-triggered scale and corner reveal
  useEffect(() => {
    if (!canPin()) return;

    const card = cardRef.current;
    const section = sectionRef.current;
    if (!card || !section) return;

    let cancelled = false;
    let context: { revert: () => void } | undefined;

    void loadScroll().then(({ gsap }) => {
      if (cancelled) return;

      context = gsap.context(() => {
        gsap.fromTo(
          card,
          {
            scale: 1.05,
            borderRadius: "0px",
          },
          {
            scrollTrigger: {
              trigger: section,
              start: "top 70%",
              end: "top 30%",
              scrub: 0.8,
            },
            scale: 1,
            borderRadius: "24px",
            ease: "none",
          }
        );
      });
    });

    return () => {
      cancelled = true;
      context?.revert();
    };
  }, []);

  return (
    <section ref={sectionRef} className="relative overflow-hidden bg-ink px-5 py-24 lg:px-8 lg:py-32">
      <div className="relative mx-auto w-full max-w-7xl">
        <div
          ref={cardRef}
          className="relative isolate overflow-hidden px-8 py-20 lg:px-16 lg:py-28"
          style={{
            background:
              "radial-gradient(ellipse 120% 80% at 50% 100%, rgba(255, 255, 255, 0.15) 0%, rgba(251, 146, 60, 0.4) 35%, rgba(220, 38, 38, 0.6) 70%, rgba(0, 0, 0, 1) 100%)",
          }}
        >
          {/* Expanding glow */}
          <div
            className="pointer-events-none absolute inset-x-0 bottom-0 h-full"
            style={{
              background:
                "radial-gradient(ellipse 100% 60% at 50% 100%, rgba(251, 146, 60, 0.3) 0%, transparent 60%)",
              filter: "blur(40px)",
            }}
            aria-hidden="true"
          />

          {/* Content */}
          <div className="relative z-10 mx-auto max-w-3xl text-center">
            <WordReveal mode="scroll" triggerRef={sectionRef} className="text-display-sm text-balance">
              Start With the Evidence.
            </WordReveal>

            <p className="mx-auto mt-6 max-w-xl text-[15px] leading-relaxed text-white/90">
              Explore procurement records, connect documents and understand the relationships behind every decision.
            </p>

            <div className="mt-8 animate-rise" style={{ animationDelay: "400ms" }}>
              <Button size="lg" variant="default" asChild className="bg-white text-zinc-900 hover:bg-white/90">
                <Link to="/login">
                  Open Workspace
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
