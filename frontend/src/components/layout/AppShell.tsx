import { Suspense, useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ChevronsLeft, ChevronsRight, LogOut, Menu, ShieldCheck, UserRound, X } from "lucide-react";

import { Logo, LogoMark } from "@/components/brand/Logo";
import { LoadingState } from "@/components/common/States";
import { SystemStatusSummary } from "@/components/common/SystemStatus";
import { WorldStage } from "@/components/world/WorldStage";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/misc";
import { api } from "@/lib/api";
import { WORLD_ENABLED } from "@/lib/features";
import { NAV_SECTIONS, routeMeta } from "@/lib/navigation";
import { cn, titleCase } from "@/lib/utils";
import { useAuth } from "@/store/auth";
import { useUi } from "@/store/ui";

export function AppShell() {
  const { user, logout, refreshUser, token } = useAuth();
  const { sidebarCollapsed, toggleSidebar } = useUi();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const mainRef = useRef<HTMLElement>(null);
  const meta = routeMeta(location.pathname);

  useEffect(() => {
    if (token && !user) void refreshUser();
  }, [token, user, refreshUser]);

  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  // A new page starts at its own top, not at the previous page's scroll offset.
  useEffect(() => {
    mainRef.current?.scrollTo({ top: 0 });
    window.scrollTo({ top: 0 });
  }, [location.pathname]);

  useEffect(() => {
    if (!drawerOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setDrawerOpen(false);
        menuButtonRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [drawerOpen]);

  const health = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 30_000,
    enabled: Boolean(token),
  });

  const sections = NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => !item.permission || user?.permissions?.includes(item.permission)),
  })).filter((section) => section.items.length > 0);

  const initials = (user?.full_name || user?.email || "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  const nav = (
    <nav aria-label="Workspace" className="flex-1 space-y-6 overflow-y-auto px-3 py-5 scrollbar-thin">
      {sections.map((section) => (
        <div key={section.label}>
          <p
            className={cn(
              "px-3 pb-2 text-[10px] font-medium uppercase tracking-[0.16em] text-subtle",
              sidebarCollapsed ? "lg:sr-only" : null,
            )}
          >
            {section.label}
          </p>
          <ul className="space-y-0.5">
            {section.items.map((item) => {
              const isActive = location.pathname === item.to || location.pathname.startsWith(`${item.to}/`);
              return (
                <li key={item.to}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <NavLink
                        to={item.to}
                        aria-current={isActive ? "page" : undefined}
                        className={cn(
                          "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-colors duration-control",
                          isActive
                            ? "bg-[#FF4D00]/10 font-semibold text-white border border-[#FF4D00]/25"
                            : "text-white/60 hover:bg-white/[0.045] hover:text-white",
                        )}
                      >
                        {/* The active marker is an orange hairline */}
                        <span
                          aria-hidden="true"
                          className={cn(
                            "absolute left-0 top-1/2 h-5 w-[2.5px] -translate-y-1/2 rounded-full bg-[#FF4D00] transition-opacity",
                            isActive ? "opacity-100" : "opacity-0",
                          )}
                        />
                        <item.icon
                          className={cn(
                            "h-4 w-4 shrink-0 transition-colors",
                            isActive ? "text-[#FF4D00]" : "text-white/45 group-hover:text-white/80",
                          )}
                          aria-hidden="true"
                        />
                        <span className={cn("truncate", sidebarCollapsed ? "lg:sr-only" : null)}>{item.label}</span>
                      </NavLink>
                    </TooltipTrigger>
                    {sidebarCollapsed ? (
                      <TooltipContent side="right" className="lg:block">
                        {item.label}
                      </TooltipContent>
                    ) : null}
                  </Tooltip>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex min-h-screen bg-ink">
        <a href="#workspace-main" className="skip-link">
          Skip to content
        </a>

        {/* The ambient light behind the workspace: one soft wash, no animation. */}
        <div
          className="pointer-events-none fixed inset-x-0 top-0 z-0 h-[420px] bg-[radial-gradient(ellipse_60%_100%_at_50%_0%,rgba(255,255,255,0.055),transparent_70%)]"
          aria-hidden="true"
        />

        {drawerOpen ? (
          <button
            type="button"
            aria-label="Close navigation"
            className="fixed inset-0 z-35 bg-black/70 backdrop-blur-sm lg:hidden"
            onClick={() => setDrawerOpen(false)}
          />
        ) : null}

        <aside
          id="workspace-sidebar"
          aria-label="Workspace navigation"
          className={cn(
            "fixed inset-y-0 left-0 z-40 flex w-[264px] shrink-0 flex-col border-r border-white/[0.08] bg-ink-2/95 backdrop-blur-xl transition-[transform,width] duration-panel lg:sticky lg:top-0 lg:h-screen lg:translate-x-0",
            drawerOpen ? "translate-x-0" : "-translate-x-full",
            sidebarCollapsed ? "lg:w-[76px]" : "lg:w-[264px]",
          )}
        >
          <div className="flex items-center justify-between px-4 py-4">
            <NavLink to="/ask" className="min-w-0">
              <span className={cn("flex items-center", sidebarCollapsed ? "lg:hidden" : null)}>
                <Logo />
                <span className="sr-only">— go to Ask</span>
              </span>
              {sidebarCollapsed ? (
                <span className="hidden h-9 w-9 items-center justify-center rounded-lg bg-white text-ink lg:flex">
                  <LogoMark className="h-[18px] w-[18px]" />
                </span>
              ) : null}
            </NavLink>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              aria-label="Close navigation"
              onClick={() => setDrawerOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="mx-4 h-px bg-white/[0.07]" />

          {nav}

          <div className="mx-4 h-px bg-white/[0.07]" />

          <div className="space-y-3 px-3 py-4">
            <div className={cn("flex items-center gap-2.5 px-1", sidebarCollapsed ? "lg:justify-center" : null)}>
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/15 bg-white/[0.06] text-[11px] font-medium">
                {initials || "EP"}
              </span>
              <div className={cn("min-w-0", sidebarCollapsed ? "lg:sr-only" : null)}>
                <p className="truncate text-[12.5px] font-medium">{user?.full_name || user?.email}</p>
                <p className="truncate text-[11px] text-subtle">
                  {titleCase(user?.role)} · {user?.permissions?.length ?? 0} permissions
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                aria-label={sidebarCollapsed ? "Expand navigation" : "Collapse navigation"}
                aria-expanded={!sidebarCollapsed}
                aria-controls="workspace-sidebar"
                className="hidden lg:inline-flex"
              >
                {sidebarCollapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className={cn("justify-start gap-2 text-muted-foreground", sidebarCollapsed ? "lg:sr-only" : null)}
                onClick={() => {
                  logout();
                  navigate("/login", { replace: true });
                }}
              >
                <LogOut className="h-4 w-4" aria-hidden="true" />
                Sign out
              </Button>
            </div>
          </div>
        </aside>

        <div className="relative z-10 flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-white/[0.07] bg-ink/75 px-4 py-3 backdrop-blur-xl lg:px-8">
            <Button
              ref={menuButtonRef}
              variant="ghost"
              size="icon"
              className="lg:hidden"
              aria-label="Open navigation"
              aria-expanded={drawerOpen}
              aria-controls="workspace-sidebar"
              onClick={() => setDrawerOpen(true)}
            >
              <Menu className="h-4 w-4" />
            </Button>

            <p className="flex min-w-0 items-center gap-2 text-[12px]">
              <span className="hidden truncate text-subtle sm:inline">{meta.section}</span>
              <span className="hidden text-white/20 sm:inline" aria-hidden="true">
                /
              </span>
              <span className="truncate font-medium text-foreground">{meta.label}</span>
            </p>

            <div className="ml-auto flex items-center gap-2">
              <SystemStatusSummary health={health.data} />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-2 rounded-full"
                    aria-label={`Account and permissions for ${user?.email ?? "this account"}`}
                  >
                    <UserRound className="h-3.5 w-3.5" aria-hidden="true" />
                    <span className="hidden max-w-[180px] truncate sm:inline">{user?.email}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>Signed in</DropdownMenuLabel>
                  <div className="px-2 pb-2 text-xs">
                    <p className="truncate font-medium">{user?.full_name || user?.email}</p>
                    <p className="truncate text-muted-foreground">{user?.email}</p>
                    <p className="mt-1 text-muted-foreground">
                      Role {titleCase(user?.role)} · access ceiling {user?.access_ceiling}
                    </p>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuLabel className="flex items-center gap-1.5">
                    <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                    Permissions on this account
                  </DropdownMenuLabel>
                  <ul className="max-h-52 overflow-y-auto px-2 pb-1 text-[11px] text-muted-foreground scrollbar-thin">
                    {(user?.permissions ?? []).map((permission) => (
                      <li key={permission} className="py-0.5 font-mono">
                        {permission}
                      </li>
                    ))}
                  </ul>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onSelect={() => {
                      logout();
                      navigate("/login", { replace: true });
                    }}
                  >
                    <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
                    Sign out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>

          <main
            ref={mainRef}
            id="workspace-main"
            className="min-h-0 flex-1 px-4 py-6 lg:px-8 lg:py-8"
          >
            <div className="mx-auto w-full max-w-[1480px]">
              {/* The 3D band is off unless VITE_ENABLE_WORLD=true at build time.
                  With the flag off the pages render in the ordinary DOM flow and
                  no three.js module is reachable from this entrypoint. */}
              {WORLD_ENABLED ? (
                <WorldStage>
                  <PageOutlet pathname={location.pathname} />
                </WorldStage>
              ) : (
                <PageOutlet pathname={location.pathname} />
              )}
            </div>
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}

/**
 * A route change is a short fade-and-lift on the new page only. Keying on the
 * pathname remounts the wrapper so the animation runs once per navigation, and
 * the reduced-motion rule in `index.css` removes it entirely when asked.
 */
function PageOutlet({ pathname }: { pathname: string }) {
  return (
    <div key={pathname} className="animate-page">
      <Suspense fallback={<LoadingState label="Loading this workspace view" />}>
        <Outlet />
      </Suspense>
    </div>
  );
}
