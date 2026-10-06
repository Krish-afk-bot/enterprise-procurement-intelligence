import { Suspense } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { Logo } from "@/components/brand/Logo";
import { LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const PUBLIC_NAV = [
  { to: "/", label: "Product" },
  { to: "/security", label: "Security" },
  { to: "/privacy", label: "Privacy" },
  { to: "/terms", label: "Terms" },
];

export function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <a href="#public-main" className="skip-link">
        Skip to content
      </a>

      <header className="sticky top-0 z-20 border-b bg-background/85 backdrop-blur">
        <div className="mx-auto flex w-full max-w-6xl items-center gap-4 px-4 py-3 lg:px-6">
          <Link to="/" className="shrink-0" aria-label="Procurement Intelligence home">
            <Logo />
          </Link>
          <nav aria-label="Product information" className="ml-auto hidden items-center gap-1 md:flex">
            {PUBLIC_NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-1.5 text-sm transition-colors duration-micro",
                    isActive ? "bg-accent font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 md:ml-0">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/login">Sign in</Link>
            </Button>
            <Button size="sm" asChild>
              <Link to="/login">Open workspace</Link>
            </Button>
          </div>
        </div>
      </header>

      <main id="public-main" className="flex-1">
        <Suspense fallback={<LoadingState label="Loading page" className="mx-auto max-w-6xl px-4 lg:px-6" />}>
          <Outlet />
        </Suspense>
      </main>

      <footer className="border-t">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-6 text-xs text-muted-foreground lg:px-6">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
            <span className="font-medium text-foreground">Procurement Intelligence</span>
            <Link to="/security" className="hover:underline">
              Security
            </Link>
            <Link to="/privacy" className="hover:underline">
              Privacy
            </Link>
            <Link to="/terms" className="hover:underline">
              Terms
            </Link>
            <Link to="/login" className="hover:underline">
              Sign in
            </Link>
          </div>
          <p className="max-w-3xl leading-relaxed">
            This is a working deployment, not a hosted commercial service. The statements on these pages describe what
            this build actually does. Where a capability is planned rather than implemented, it is labelled as such.
          </p>
        </div>
      </footer>
    </div>
  );
}
