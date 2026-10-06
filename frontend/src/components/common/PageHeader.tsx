import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * One header pattern for every workspace page: a title, one line of context, and
 * the actions that belong to the page.
 */
export function PageHeader({
  title,
  description,
  actions,
  backTo,
  backLabel,
  meta,
  className,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  backTo?: string;
  backLabel?: string;
  meta?: React.ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("flex flex-wrap items-start justify-between gap-3", className)}>
      <div className="flex min-w-0 items-start gap-2">
        {backTo ? (
          <Button variant="ghost" size="icon" asChild className="-ml-2 mt-0.5">
            <Link to={backTo} aria-label={backLabel ?? "Back"}>
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
        ) : null}
        <div className="min-w-0">
          <h1 className="truncate text-lg font-semibold tracking-tight">{title}</h1>
          {description ? (
            <p className="mt-0.5 max-w-3xl text-xs leading-relaxed text-muted-foreground">{description}</p>
          ) : null}
          {meta ? <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">{meta}</div> : null}
        </div>
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

/** Label plus value, used in metadata rows rather than a card per field. */
export function MetaItem({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="text-xs font-medium">{children}</span>
    </span>
  );
}
