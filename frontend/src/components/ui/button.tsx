import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

/**
 * Buttons.
 *
 * The action colour is white: a filled white control with a black label is the
 * single highest-contrast element on the page, so a screen can have one without
 * needing an accent hue. `glow` adds the soft white halo reserved for the
 * landing page's primary call to action.
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-medium transition-[background-color,color,border-color,box-shadow,transform] duration-control ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-45 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-white text-ink shadow-[inset_0_1px_0_0_rgb(255_255_255_/_0.6)] hover:bg-white/90 hover:shadow-glow",
        /* The hero CTA: white fill with a standing halo that grows on hover. */
        glow:
          "bg-white text-ink shadow-glow hover:-translate-y-0.5 hover:bg-white hover:shadow-glow-lg active:translate-y-0",
        destructive: "bg-destructive/90 text-destructive-foreground hover:bg-destructive",
        outline:
          "border border-white/15 bg-white/[0.03] text-foreground hover:border-white/30 hover:bg-white/[0.07]",
        secondary: "bg-white/[0.07] text-foreground hover:bg-white/[0.12]",
        ghost: "text-muted-foreground hover:bg-white/[0.06] hover:text-foreground",
        link: "text-foreground underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-full px-3.5 text-xs",
        lg: "h-11 px-7 text-[15px]",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
