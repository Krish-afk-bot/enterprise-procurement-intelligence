import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

/**
 * Badges are hairlines, not colour chips.
 *
 * Status is carried by the text and by one restrained semantic tone, so a table
 * of twenty rows does not turn into a traffic-light wall.
 */
const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium leading-5 tracking-wide transition-colors",
  {
    variants: {
      variant: {
        default: "border-white/15 bg-white/[0.06] text-foreground",
        secondary: "border-transparent bg-white/[0.08] text-foreground",
        destructive: "border-destructive/40 bg-destructive/10 text-destructive",
        success: "border-success/40 bg-success/10 text-success",
        warning: "border-warning/40 bg-warning/10 text-warning",
        outline: "border-white/15 text-muted-foreground",
      },
    },
    defaultVariants: { variant: "outline" },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

/**
 * A badge is a plain div, but it is also used as the child of Radix triggers
 * (`asChild`), which clone their child and attach a ref. Forwarding the ref is
 * what makes that work without React warning about function components.
 */
const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(({ className, variant, ...props }, ref) => (
  <div ref={ref} className={cn(badgeVariants({ variant }), className)} {...props} />
));
Badge.displayName = "Badge";

export { Badge, badgeVariants };
