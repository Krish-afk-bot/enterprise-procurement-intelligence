import { cn } from "@/lib/utils";

/**
 * The product mark is a table glyph: a price schedule with a header row and a
 * column divider. It reads as procurement records rather than as "AI".
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={cn("h-6 w-6", className)}
      strokeWidth={1.9}
      strokeLinecap="round"
    >
      <rect x="4.5" y="5.5" width="23" height="21" rx="3.4" stroke="currentColor" />
      <path d="M4.5 12h23" stroke="currentColor" />
      <path d="M12.6 12v14.5" stroke="currentColor" />
    </svg>
  );
}

export function Logo({
  compact = false,
  className,
}: {
  compact?: boolean;
  className?: string;
}) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <LogoMark className="h-[18px] w-[18px]" />
      </span>
      {compact ? null : (
        <span className="min-w-0 leading-tight">
          <span className="block truncate text-[13px] font-semibold tracking-tight">Procurement Intelligence</span>
          <span className="block truncate text-[11px] text-muted-foreground">Contract and pricing evidence</span>
        </span>
      )}
    </span>
  );
}
