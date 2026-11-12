import { Suspense, useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";

import { Logo } from "@/components/brand/Logo";
import { LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { useSeo } from "@/lib/seo";
import { cn } from "@/lib/utils";

const PUBLIC_NAV = [
  { to: "/", label: "Product" },
  { to: "/security", label: "Security" },
  { to: "/privacy", label: "Privacy" },
  { to: "/terms", label: "Terms" },
];

const PAGE_META: Record<string, { title: string; description: string }> = {
  "/": {
    title: "EPI — Enterprise Procurement Intelligence, powered by evidence",
    description:
      "Search procurement records, supplier agreements, pricing schedules, amendments and compliance documents, then open the exact page each answer was built from.",
  },
  "/security": {
    title: "Security model — EPI",
    description:
      "Tenant isolation, authenticated sessions, server-enforced permissions, document access levels and an audit trail — with the controls this build does not implement listed explicitly.",
  },
  "/privacy": {
    title: "Privacy — EPI",
    description:
      "What this self-hosted procurement workspace stores, where it is stored, what it never does with your documents, and how retention works.",
  },
  "/terms": {
    title: "Terms — EPI",
    description:
      "The conditions for using this evaluation build, including the limits of extraction and verification and the status of the bundled corpus.",
  },
};

export function PublicLayout() {
  // The header starts transparent over the hero and gains a surface once the
  // page scrolls, so the cinematic opening is not cut by a bar.
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const progressRef = useRef<HTMLSpanElement>(null);
  const location = useLocation();
  useSeo(PAGE_META[location.pathname] ?? PAGE_META["/"]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // A route change always closes the drawer, even when the link was a hash.
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname, location.hash]);

  // Reading progress for the public pages. Written straight to a ref so the
  // header never re-renders while the reader scrolls.
  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const value = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
      if (progressRef.current) progressRef.current.style.transform = `scaleX(${value})`;
    };
    const onScroll = () => {
      if (!frame) frame = window.requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [menuOpen]);

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <a href="#public-main" className="skip-link">
        Skip to content
      </a>

      <header
        className={cn(
          "fixed inset-x-0 top-0 z-40 transition-[background-color,border-color,backdrop-filter] duration-300",
          scrolled || menuOpen
            ? "border-b border-white/[0.08] bg-ink/80 backdrop-blur-xl"
            : "border-b border-transparent bg-transparent",
        )}
      >
        <div className="mx-auto flex w-full max-w-7xl items-center gap-6 px-5 py-3.5 lg:px-8">
          {/* The accessible name includes the visible wordmark and tagline, so a
              speech input user can say what they see. */}
          <Link to="/" className="shrink-0" aria-label="Procurement Intelligence — Contract and pricing evidence, home">
            <Logo />
          </Link>

          <nav aria-label="Product information" className="ml-auto hidden items-center gap-1 lg:flex">
            <Link
              to="/#platform"
              className="rounded-full px-3.5 py-1.5 text-[13px] text-muted-foreground transition-colors duration-control hover:bg-white/[0.05] hover:text-foreground"
            >
              Platform
            </Link>
            {PUBLIC_NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "rounded-full px-3.5 py-1.5 text-[13px] transition-colors duration-control",
                    isActive
                      ? "bg-white/[0.08] text-foreground"
                      : "text-muted-foreground hover:bg-white/[0.05] hover:text-foreground",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2 lg:ml-0">
            <Button variant="ghost" size="sm" asChild className="hidden sm:inline-flex">
              <Link to="/login">Sign in</Link>
            </Button>
            <Button size="sm" asChild className="hidden lg:inline-flex">
              <Link to="/login">Open workspace</Link>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              aria-label={menuOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={menuOpen}
              aria-controls="public-mobile-navigation"
              onClick={() => setMenuOpen((value) => !value)}
            >
              {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </div>

        {/* Mobile drawer: a slide-down panel rather than a full-screen takeover,
            so the hero stays visible behind it. */}
        <div
          id="public-mobile-navigation"
          hidden={!menuOpen}
          className="border-t border-white/[0.08] bg-ink/95 px-5 pb-6 pt-2 backdrop-blur-xl lg:hidden"
        >
          <nav aria-label="Product information, mobile" className="flex flex-col">
            <Link
              to="/#platform"
              className="flex min-h-[44px] items-center rounded-lg px-3 text-[14px] text-muted-foreground transition-colors hover:text-foreground"
            >
              Platform
            </Link>
            {PUBLIC_NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex min-h-[44px] items-center rounded-lg px-3 text-[14px] transition-colors",
                    isActive ? "bg-white/[0.07] text-foreground" : "text-muted-foreground hover:text-foreground",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-4 grid gap-2">
            <Button asChild className="w-full">
              <Link to="/login">Open workspace</Link>
            </Button>
            <Button variant="outline" asChild className="w-full">
              <Link to="/login">Sign in</Link>
            </Button>
          </div>
        </div>

        <span aria-hidden="true" className="absolute inset-x-0 bottom-0 h-px overflow-hidden">
          <span
            ref={progressRef}
            className="block h-px w-full origin-left bg-white/40"
            style={{ transform: "scaleX(0)" }}
          />
        </span>
      </header>

      <main id="public-main" className="flex-1">
        <Suspense fallback={<LoadingState label="Loading page" className="mx-auto max-w-6xl px-4 pt-32 lg:px-6" />}>
          <Outlet />
        </Suspense>
      </main>

      <footer className="relative border-t border-white/[0.08] bg-ink-2">
        <div className="mx-auto w-full max-w-7xl px-5 py-12 lg:px-8">
          <div className="flex flex-col gap-10 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-sm">
              <Logo />
              <p className="mt-4 text-[13px] leading-relaxed text-muted-foreground">
                Find the contract terms, prices and compliance requirements behind every procurement decision — with the
                page each answer came from attached to it.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-x-12 gap-y-8 text-[13px] sm:grid-cols-3">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-subtle">Product</p>
                <ul className="mt-3 space-y-2">
                  <li>
                    <Link to="/" className="text-muted-foreground transition-colors hover:text-foreground">
                      Overview
                    </Link>
                  </li>
                  <li>
                    <Link to="/login" className="text-muted-foreground transition-colors hover:text-foreground">
                      Workspace
                    </Link>
                  </li>
                  <li>
                    <Link to="/security" className="text-muted-foreground transition-colors hover:text-foreground">
                      Security
                    </Link>
                  </li>
                </ul>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-subtle">Deployment</p>
                <ul className="mt-3 space-y-2">
                  <li>
                    <Link to="/privacy" className="text-muted-foreground transition-colors hover:text-foreground">
                      Privacy
                    </Link>
                  </li>
                  <li>
                    <Link to="/terms" className="text-muted-foreground transition-colors hover:text-foreground">
                      Terms
                    </Link>
                  </li>
                  <li>
                    <Link to="/login" className="text-muted-foreground transition-colors hover:text-foreground">
                      Sign in
                    </Link>
                  </li>
                </ul>
              </div>
              <div className="col-span-2 sm:col-span-1">
                <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-subtle">Status</p>
                <p className="mt-3 flex items-center gap-2 text-muted-foreground">
                  <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />
                  Working deployment
                </p>
              </div>
            </div>
          </div>

          <div className="mt-12 flex flex-col gap-3 border-t border-white/[0.07] pt-6 text-[11px] leading-relaxed text-subtle sm:flex-row sm:items-center sm:justify-between">
            <p>Procurement Intelligence</p>
            <p className="max-w-2xl">
              This is a working deployment, not a hosted commercial service. Statements on these pages describe what
              this build actually does; a capability that is planned rather than implemented is labelled as such.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
