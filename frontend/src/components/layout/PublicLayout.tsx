import { Suspense } from "react";
import { Outlet } from "react-router-dom";
import { SiteHeader } from "@/components/navigation/SiteHeader";
import { LandingFooter } from "@/components/sections/LandingFooter";
import { LoadingState } from "@/components/common/States";

export function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-[#050505] text-white selection:bg-[#FF4D00] selection:text-white">
      <a href="#public-main" className="skip-link sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[110] focus:px-4 focus:py-2 focus:bg-[#FF4D00] focus:text-white focus:rounded-md">
        Skip to content
      </a>

      {/* Exactly ONE Unified Header */}
      <SiteHeader />

      <main id="public-main" className="flex-1 w-full">
        <Suspense fallback={<LoadingState label="Loading page" className="mx-auto max-w-6xl px-4 pt-32 lg:px-6" />}>
          <Outlet />
        </Suspense>
      </main>

      {/* Exactly ONE Unified Footer */}
      <LandingFooter />
    </div>
  );
}
