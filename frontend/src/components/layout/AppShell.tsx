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
import { Separator, Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/misc";
import { api } from "@/lib/api";
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
  const meta = routeMeta(location.pathname);

  useEffect(() => {
    if (token && !user) void refreshUser();
  }, [token, user, refreshUser]);

  useEffect(() => {
    setDrawerOpen(false);
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

  const nav = (
    <nav aria-label="Workspace" className="flex-1 space-y-5 overflow-y-auto px-2 py-3 scrollbar-thin">
      {sections.map((section) => (
        <div key={section.label}>
          <p
            className={cn(
              "px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground",
              sidebarCollapsed ? "lg:sr-only" : null,
            )}
          >
            {section.label}
          </p>
          <ul className="space-y-0.5">
            {section.items.map((item) => (
              <li key={item.to}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <NavLink
                      to={item.to}
                      aria-current={location.pathname === item.to ? "page" : undefined}
                      className={({ isActive }) =>
                        cn(
                          "group flex items-center gap-2.5 rounded-md border-l-2 px-3 py-2 text-sm transition-colors duration-micro",
                          isActive
                            ? "border-l-primary bg-primary/10 font-medium text-primary"
                            : "border-l-transparent text-muted-foreground hover:bg-accent hover:text-foreground",
                        )
                      }
                    >
                      <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
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
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex min-h-screen bg-background">
        <a href="#workspace-main" className="skip-link">
          Skip to content
        </a>

        {drawerOpen ? (
          <button
            type="button"
            aria-label="Close navigation"
            className="fixed inset-0 z-35 bg-foreground/20 lg:hidden"
            onClick={() => setDrawerOpen(false)}
          />
        ) : null}

        <aside
          id="workspace-sidebar"
          aria-label="Workspace navigation"
          className={cn(
            "fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col border-r bg-card transition-[transform,width] duration-panel lg:sticky lg:top-0 lg:h-screen lg:translate-x-0",
            drawerOpen ? "translate-x-0" : "-translate-x-full",
            sidebarCollapsed ? "lg:w-[68px]" : "lg:w-64",
          )}
        >
          <div className="flex items-center justify-between px-3 py-3.5">
            <NavLink to="/ask" className="min-w-0" aria-label="Procurement Intelligence, go to Ask">
              <span className={cn("flex items-center", sidebarCollapsed ? "lg:hidden" : null)}>
                <Logo />
              </span>
              {sidebarCollapsed ? (
                <span className="hidden h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground lg:flex">
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
          <Separator />
          {nav}
          <Separator />
          <div className="space-y-2 px-2 py-3">
            <div className={cn("min-w-0", sidebarCollapsed ? "lg:sr-only" : null)}>
              <p className="truncate px-1 text-xs font-medium">{user?.full_name || user?.email}</p>
              <p className="truncate px-1 text-[11px] text-muted-foreground">
                {titleCase(user?.role)} · {user?.permissions?.length ?? 0} permissions
              </p>
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
                className={cn("justify-start gap-2", sidebarCollapsed ? "lg:sr-only" : null)}
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

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 flex items-center gap-3 border-b bg-background/85 px-4 py-2.5 backdrop-blur lg:px-6">
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

            <p className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
              <span className="hidden truncate sm:inline">{meta.section}</span>
              <span className="hidden sm:inline" aria-hidden="true">
                /
              </span>
              <span className="truncate font-medium text-foreground">{meta.label}</span>
            </p>

            <div className="ml-auto flex items-center gap-2">
              <SystemStatusSummary health={health.data} />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-2" aria-label="Account and permissions">
                    <UserRound className="h-3.5 w-3.5" aria-hidden="true" />
                    <span className="hidden max-w-[160px] truncate sm:inline">{user?.email}</span>
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

          <main id="workspace-main" className="min-h-0 flex-1 px-4 py-5 lg:px-6 lg:py-6">
            <div className="mx-auto w-full max-w-[1400px]">
              {/* The band is the workspace's persistent 3D strip. It also owns the
                  context every page scene reads, so a scene can tell whether it
                  should draw into the shared canvas or write its own. */}
              <WorldStage>
                <Suspense fallback={<LoadingState label="Loading this workspace view" />}>
                  <Outlet />
                </Suspense>
              </WorldStage>
            </div>
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
