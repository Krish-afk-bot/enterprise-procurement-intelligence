import { useState } from "react";
import { Link } from "react-router-dom";
import { LANDING_CONTENT } from "@/content/landing";
import { Logo } from "@/components/brand/Logo";
import { useMotionMode, setMotionPref, MotionPref } from "@/motion/motion";
import { cn } from "@/lib/utils";

export function LandingFooter() {
  const motionMode = useMotionMode();
  const [pref, setPrefState] = useState<MotionPref>(() => {
    if (typeof localStorage !== "undefined") {
      return (localStorage.getItem("epi-motion") as MotionPref) || "system";
    }
    return "system";
  });

  const handleMotionChange = (newPref: MotionPref) => {
    setPrefState(newPref);
    setMotionPref(newPref);
  };

  return (
    <footer className="relative bg-[#050505] text-white pt-20 pb-12 px-6 border-t border-white/10 overflow-hidden">
      {/* Subtle upper-right orange glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-[#FF4D00]/10 to-transparent rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-7xl mx-auto relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-[1.4fr_repeat(4,1fr)] gap-10 mb-16">
          {/* Brand Col */}
          <div>
            <div className="mb-4">
              <Logo variant="lockup" size={34} />
            </div>
            <p className="text-sm text-white/50 max-w-sm mb-6 leading-relaxed">
              {LANDING_CONTENT.footer.tagline}
            </p>
            <div className="text-xs font-mono text-white/35">
              Strict multi-tenant isolation • Verifiable source traceability
            </div>

            {/* Accessible Motion Mode Selector (A2) */}
            <div className="mt-6 flex flex-col gap-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-white/50">
                Motion Experience ({motionMode})
              </span>
              <div className="inline-flex items-center rounded-full border border-white/10 bg-white/[0.03] p-1 w-fit">
                {(["system", "full", "reduced", "off"] as const).map((modeOption) => (
                  <button
                    key={modeOption}
                    type="button"
                    onClick={() => handleMotionChange(modeOption)}
                    className={cn(
                      "px-3 py-1 rounded-full text-[11px] font-medium capitalize transition-colors",
                      pref === modeOption
                        ? "bg-[#FF4D00] text-white shadow-sm"
                        : "text-white/60 hover:text-white"
                    )}
                  >
                    {modeOption}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 4 Equal Nav Columns in One Row: Platform, Intelligence, Governance, Access */}
          {LANDING_CONTENT.footer.columns.map((col) => (
            <div key={col.title}>
              <h4 className="text-xs font-mono uppercase tracking-widest text-[#FF4D00] font-semibold mb-4">
                {col.title}
              </h4>
              <ul className="flex flex-col gap-2.5">
                {col.links.map((link) => (
                  <li key={link.label}>
                    {link.href.startsWith("/") && !link.href.startsWith("/#") ? (
                      <Link
                        to={link.href}
                        className="text-xs text-white/60 hover:text-white transition-colors"
                      >
                        {link.label}
                      </Link>
                    ) : (
                      <a
                        href={link.href}
                        className="text-xs text-white/60 hover:text-white transition-colors"
                      >
                        {link.label}
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-white/40">
          <span>{LANDING_CONTENT.footer.copyright}</span>
          <div className="flex items-center gap-6">
            <Link to="/security" className="hover:text-white transition-colors">
              Security
            </Link>
            <Link to="/privacy" className="hover:text-white transition-colors">
              Privacy
            </Link>
            <Link to="/terms" className="hover:text-white transition-colors">
              Terms
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
