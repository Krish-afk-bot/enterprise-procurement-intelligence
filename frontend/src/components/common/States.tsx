import type { LucideIcon } from "lucide-react";
import { AlertTriangle, Inbox, Loader2, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { NOT_RECORDED, cn } from "@/lib/utils";

export function LoadingRows({ rows = 4, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-2", className)} aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className="h-9 w-full" />
      ))}
    </div>
  );
}

/**
 * `label` must describe the operation the platform is actually performing, so a
 * spinner never claims progress the system did not report.
 */
export function LoadingState({ label, className }: { label: string; className?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("flex items-center gap-2 py-5 text-sm text-muted-foreground", className)}
    >
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      {label}
    </div>
  );
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center gap-2.5 rounded-lg border border-dashed px-6 py-10 text-center", className)}>
      <Icon className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
      <p className="text-sm font-medium">{title}</p>
      {description ? <p className="max-w-md text-xs leading-relaxed text-muted-foreground">{description}</p> : null}
      {action ? <div className="pt-1">{action}</div> : null}
    </div>
  );
}

export function ErrorState({ error, onRetry, hint }: { error: unknown; onRetry?: () => void; hint?: string }) {
  const message = error instanceof Error ? error.message : "The request failed.";
  return (
    <div role="alert" className="flex flex-col items-start gap-2 rounded-lg border border-destructive/35 bg-destructive/5 p-4">
      <p className="flex items-center gap-2 text-sm font-medium">
        <AlertTriangle className="h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
        {message}
      </p>
      <p className="text-xs leading-relaxed text-muted-foreground">
        {hint ??
          "A failed lookup is never rendered as an empty result, so this panel shows the failure instead of missing data."}
      </p>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" />
          Retry
        </Button>
      ) : null}
    </div>
  );
}

/** Explicit placeholder for a value the platform does not hold. */
export function NotAvailable({ label = NOT_RECORDED }: { label?: string }) {
  return <span className="text-xs italic text-muted-foreground">{label}</span>;
}

export function SectionHeading({
  title,
  description,
  actions,
  as: As = "h2",
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  as?: "h2" | "h3";
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <As className="text-sm font-semibold tracking-tight">{title}</As>
        {description ? <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
