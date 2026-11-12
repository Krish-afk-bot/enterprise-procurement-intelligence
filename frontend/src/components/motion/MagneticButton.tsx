import { useMagneticHover } from "@/lib/useMagneticHover";
import { cn } from "@/lib/utils";

/**
 * A button wrapper that adds magnetic hover behavior.
 *
 * The button subtly follows the pointer when nearby, creating a premium
 * interaction feel. Desktop-only, fine-pointer-only, off for reduced motion.
 */
export function MagneticButton({
  children,
  className,
  strength = 0.35,
  radius = 90,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  strength?: number;
  radius?: number;
}) {
  const ref = useMagneticHover<HTMLButtonElement>(strength, radius);

  return (
    <button
      ref={ref}
      className={cn(
        "relative inline-flex items-center justify-center transition-transform duration-200 ease-out will-change-transform",
        className,
      )}
      {...props}
    >
      <span className="relative z-10">{children}</span>
    </button>
  );
}
