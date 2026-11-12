import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV_SECTIONS = [
  { id: "hero", label: "Home", href: "#hero" },
  { id: "platform", label: "Platform", href: "#platform" },
  { id: "capabilities", label: "Capabilities", href: "#capabilities" },
  { id: "globe", label: "Network", href: "#globe" },
  { id: "evidence-demo", label: "Demo", href: "#evidence-demo" },
  { id: "use-cases", label: "Use Cases", href: "#use-cases" },
];

/**
 * Adaptive Navigation Pill.
 *
 * Features:
 * - Floating pill that appears after scrolling
 * - Changes theme based on section (dark/light)
 * - Active section indicator
 * - Smooth theme transitions
 * - Mobile responsive
 */
export function AdaptiveNav() {
  const [visible, setVisible] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [activeSection, setActiveSection] = useState("hero");

  // Show/hide based on scroll
  useEffect(() => {
    const onScroll = () => {
      setVisible(window.scrollY > 100);
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Detect active section and theme
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const sectionId = entry.target.id;
            setActiveSection(sectionId);

            // Determine theme based on section
            const lightSections = ["platform", "use-cases", "evidence-demo"];
            setTheme(lightSections.includes(sectionId) ? "light" : "dark");
          }
        });
      },
      {
        rootMargin: "-50% 0px -50% 0px",
        threshold: 0,
      }
    );

    // Observe all nav sections
    NAV_SECTIONS.forEach((section) => {
      const element = document.getElementById(section.id);
      if (element) observer.observe(element);
    });

    return () => observer.disconnect();
  }, []);

  if (!visible) return null;

  const isDark = theme === "dark";

  return (
    <nav
      className={cn(
        "fixed left-1/2 top-6 z-50 -translate-x-1/2 transition-all duration-500 ease-out",
        visible ? "translate-y-0 opacity-100" : "-translate-y-4 opacity-0"
      )}
      aria-label="Main navigation"
    >
      <div
        className={cn(
          "flex items-center gap-4 rounded-full border px-3 py-2 shadow-lg backdrop-blur-xl transition-colors duration-500",
          isDark
            ? "border-white/10 bg-zinc-900/80"
            : "border-zinc-200/80 bg-white/80"
        )}
      >
        {/* Logo tile */}
        <div
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-lg transition-colors duration-500",
            isDark ? "bg-orange-500/20" : "bg-orange-500/10"
          )}
        >
          <div className="scale-75">
            <Logo />
          </div>
        </div>

        {/* Navigation links (desktop) */}
        <div className="hidden items-center gap-1 md:flex">
          {NAV_SECTIONS.map((section) => (
            <a
              key={section.id}
              href={section.href}
              className={cn(
                "rounded-full px-3 py-1.5 text-[13px] font-medium transition-all duration-300",
                activeSection === section.id
                  ? isDark
                    ? "bg-white/10 text-white"
                    : "bg-zinc-900/10 text-zinc-900"
                  : isDark
                    ? "text-white/60 hover:bg-white/5 hover:text-white/90"
                    : "text-zinc-600 hover:bg-zinc-900/5 hover:text-zinc-900"
              )}
            >
              {section.label}
            </a>
          ))}
        </div>

        {/* CTA */}
        <Button
          size="sm"
          asChild
          className={cn(
            "h-9 rounded-full transition-colors duration-500",
            isDark
              ? "bg-white text-zinc-900 hover:bg-white/90"
              : "bg-zinc-900 text-white hover:bg-zinc-800"
          )}
        >
          <Link to="/login">Open Workspace</Link>
        </Button>
      </div>
    </nav>
  );
}
