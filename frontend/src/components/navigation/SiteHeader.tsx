import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Logo } from "@/components/brand/Logo";
import { ArrowRight, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Product", href: "/#hero", anchor: "hero" },
  { label: "Platform", href: "/#bento", anchor: "bento" },
  { label: "Evidence", href: "/#demo", anchor: "demo" },
  { label: "Capabilities", href: "/#capabilities", anchor: "capabilities" },
  { label: "Security", href: "/security", isRoute: true },
];

export function SiteHeader() {
  const [scrollY, setScrollY] = useState(0);
  const [activeSection, setActiveSection] = useState("hero");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const isLanding = location.pathname === "/";

  useEffect(() => {
    const handleScroll = () => {
      setScrollY(window.scrollY);

      if (isLanding) {
        const sections = ["hero", "explainer", "bento", "globe", "demo", "use-cases", "capabilities", "faq", "cta"];
        const pos = window.scrollY + 180;
        for (const s of sections) {
          const el = document.getElementById(s);
          if (el) {
            const top = el.offsetTop;
            const h = el.offsetHeight;
            if (pos >= top && pos < top + h) {
              setActiveSection(s);
              break;
            }
          }
        }
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, [isLanding]);

  const isPill = scrollY >= 24;

  return (
    <header
      className={cn(
        "site-header fixed inset-x-0 top-0 z-[100] transition-all duration-300 pointer-events-none flex justify-center",
        isPill ? "py-3.5" : "py-5"
      )}
      data-state={isPill ? "pill" : "top"}
    >
      {/* Top viewport scrim so scrolled content fades smoothly behind floating pill */}
      {isPill && (
        <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-[#050505] via-[#050505]/80 to-transparent pointer-events-none -z-10 transition-opacity duration-300" />
      )}

      <nav
        aria-label="Primary"
        className={cn(
          "bar pointer-events-auto flex items-center justify-between transition-all duration-300",
          isPill
            ? "mx-auto w-[92%] max-w-4xl px-5 py-2.5 rounded-full bg-[#0C0C0C]/85 border border-white/12 shadow-[0_8px_32px_rgba(0,0,0,0.45)] backdrop-blur-xl"
            : "w-full max-w-7xl px-6 sm:px-8 py-3 bg-transparent border-transparent"
        )}
      >
        {/* Left: Full Lockup at top, morphs to mark only in pill */}
        <Link to="/" className="flex items-center gap-2 group shrink-0" aria-label="EPI home">
          <Logo variant="mark" size={32} />
          <span
            className={cn(
              "font-bold text-lg tracking-tight text-white transition-all duration-300 overflow-hidden whitespace-nowrap",
              isPill ? "w-0 opacity-0 -ml-2 pointer-events-none" : "w-12 opacity-100 ml-1"
            )}
          >
            EPI
          </span>
        </Link>

        {/* Center: Nav links (desktop) */}
        <div className="hidden md:flex items-center gap-1 bg-white/[0.03] border border-white/5 rounded-full px-2 py-1">
          {NAV_ITEMS.map((item) => {
            const isActive = item.isRoute
              ? location.pathname === item.href
              : isLanding && activeSection === item.anchor;

            return item.isRoute ? (
              <Link
                key={item.label}
                to={item.href}
                className={cn(
                  "relative px-3.5 py-1.5 text-[13px] font-medium tracking-wide transition-colors duration-200 rounded-full",
                  isActive ? "text-white bg-white/10" : "text-white/65 hover:text-white"
                )}
                aria-current={isActive ? "page" : undefined}
              >
                {item.label}
              </Link>
            ) : (
              <a
                key={item.label}
                href={item.href}
                className={cn(
                  "relative px-3.5 py-1.5 text-[13px] font-medium tracking-wide transition-colors duration-200 rounded-full",
                  isActive ? "text-white bg-white/10" : "text-white/65 hover:text-white"
                )}
              >
                {item.label}
              </a>
            );
          })}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-3 shrink-0">
          <Link
            to="/login"
            className="hidden sm:inline-block text-xs font-medium tracking-wide text-white/70 hover:text-white px-2 py-1.5 transition-colors"
          >
            Sign in
          </Link>
          <Link
            to="/app/dashboard"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold tracking-wide bg-[#FF4D00] text-white hover:bg-[#FF7A1A] transition-all duration-200 shadow-[0_0_20px_rgba(255,77,0,0.3)] hover:scale-[1.02]"
          >
            <span>Open workspace</span>
            <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
          </Link>

          {/* Mobile hamburger button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-full text-white/80 hover:text-white bg-white/5"
            aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </nav>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-50 bg-[#050505]/95 backdrop-blur-2xl flex flex-col p-6 pt-24 pointer-events-auto">
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="absolute top-6 right-6 p-2 rounded-full text-white/80 hover:text-white"
            aria-label="Close menu"
          >
            <X className="w-6 h-6" />
          </button>
          <div className="flex flex-col gap-4 text-lg">
            {NAV_ITEMS.map((item) => (
              <a
                key={item.label}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className="py-2 text-white/80 hover:text-white font-medium border-b border-white/5"
              >
                {item.label}
              </a>
            ))}
          </div>
          <div className="mt-auto pt-8 flex flex-col gap-3">
            <Link
              to="/login"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full text-center py-3 rounded-full border border-white/10 text-white font-medium text-sm"
            >
              Sign in
            </Link>
            <Link
              to="/app/dashboard"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full text-center py-3 rounded-full bg-[#FF4D00] text-white font-semibold text-sm"
            >
              Open workspace
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}

