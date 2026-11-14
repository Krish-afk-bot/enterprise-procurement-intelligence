import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { LANDING_CONTENT } from "@/content/landing";
import { cn } from "@/lib/utils";
import { ArrowRight, Menu, X } from "lucide-react";

export function NavigationPill() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [activeSection, setActiveSection] = useState("hero");
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);

      // Detect theme from data-active-theme or section inspection
      const activeTheme = document.body.getAttribute("data-active-theme");
      if (activeTheme === "light" || activeTheme === "dark") {
        setTheme(activeTheme);
      }

      // Check current section
      const sections = ["hero", "explainer", "bento", "globe", "demo", "use-cases", "capabilities", "faq", "cta"];
      const scrollPos = window.scrollY + 200;

      for (const sectionId of sections) {
        const el = document.getElementById(sectionId);
        if (el) {
          const top = el.offsetTop;
          const height = el.offsetHeight;
          if (scrollPos >= top && scrollPos < top + height) {
            setActiveSection(sectionId);
            break;
          }
        }
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const isDark = theme === "dark";

  return (
    <>
      {/* Floating Adaptive Nav Pill */}
      <header
        className={cn(
          "fixed top-5 left-1/2 -translate-x-1/2 z-50 transition-all duration-300 w-[92%] max-w-4xl",
          scrolled ? "top-4" : "top-6"
        )}
      >
        <div
          className={cn(
            "relative flex items-center justify-between px-5 py-3 rounded-full backdrop-blur-xl border transition-all duration-300 shadow-2xl",
            isDark
              ? "bg-[#0B0B0C]/85 border-white/10 text-white"
              : "bg-white/90 border-black/10 text-[#0A0A0A] shadow-black/10"
          )}
        >
          {/* Brand mark */}
          <a href="#hero" className="flex items-center gap-2.5 group">
            <span className="w-7 h-7 rounded-lg bg-[#FF4D00] flex items-center justify-center font-bold text-xs text-white shadow-lg shadow-[#FF4D00]/30 group-hover:scale-105 transition-transform">
              E
            </span>
            <span className="font-semibold text-sm tracking-tight hidden sm:inline-block">
              {LANDING_CONTENT.brand.name}
            </span>
          </a>

          {/* Center Links */}
          <nav className="hidden md:flex items-center gap-6">
            {LANDING_CONTENT.nav.links.map((link) => {
              const isActive = activeSection === link.href.replace("#", "");
              return (
                <a
                  key={link.label}
                  href={link.href}
                  className={cn(
                    "text-xs font-medium tracking-wide transition-colors relative py-1",
                    isDark
                      ? isActive
                        ? "text-white"
                        : "text-white/60 hover:text-white"
                      : isActive
                        ? "text-black"
                        : "text-black/60 hover:text-black"
                  )}
                >
                  {link.label}
                  {isActive && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#FF4D00] rounded-full" />
                  )}
                </a>
              );
            })}
          </nav>

          {/* Right Action Buttons */}
          <div className="flex items-center gap-3">
            <Link
              to={LANDING_CONTENT.nav.auth.signIn.href}
              className={cn(
                "hidden sm:inline-block text-xs font-medium tracking-wide px-3 py-1.5 transition-colors",
                isDark ? "text-white/70 hover:text-white" : "text-black/70 hover:text-black"
              )}
            >
              {LANDING_CONTENT.nav.auth.signIn.label}
            </Link>

            <Link
              to={LANDING_CONTENT.nav.auth.workspace.href}
              className={cn(
                "inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold tracking-wide transition-all duration-200 shadow-md",
                isDark
                  ? "bg-[#FF4D00] text-white hover:bg-[#FF7A1A] shadow-[#FF4D00]/25 hover:shadow-[#FF4D00]/40"
                  : "bg-[#0A0A0A] text-white hover:bg-black shadow-black/20"
              )}
            >
              <span>{LANDING_CONTENT.nav.auth.workspace.label}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className={cn(
                "md:hidden p-1.5 rounded-full",
                isDark ? "text-white/80 hover:text-white" : "text-black/80 hover:text-black"
              )}
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile dropdown drawer */}
        {mobileMenuOpen && (
          <div
            className={cn(
              "md:hidden mt-2 p-4 rounded-2xl border backdrop-blur-xl transition-all shadow-2xl",
              isDark
                ? "bg-[#0B0B0C]/95 border-white/10 text-white"
                : "bg-white/95 border-black/10 text-[#0A0A0A]"
            )}
          >
            <div className="flex flex-col gap-3">
              {LANDING_CONTENT.nav.links.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className="text-sm font-medium py-1.5 px-2 rounded-lg hover:bg-white/5"
                >
                  {link.label}
                </a>
              ))}
              <div className="pt-2 border-t border-white/10 flex flex-col gap-2">
                <Link
                  to={LANDING_CONTENT.nav.auth.signIn.href}
                  className="text-sm font-medium py-1.5 px-2"
                >
                  {LANDING_CONTENT.nav.auth.signIn.label}
                </Link>
              </div>
            </div>
          </div>
        )}
      </header>
    </>
  );
}
