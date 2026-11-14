import { useId } from "react";

type Props = {
  variant?: "mark" | "lockup";
  size?: number;
  theme?: "dark" | "light";
  className?: string;
  compact?: boolean;
};

export function LogoMark({ size = 32, className }: { size?: number; className?: string }) {
  const gid = useId();
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      role="img"
      aria-label="EPI"
      className={className}
    >
      <defs>
        <linearGradient id={gid} x1="8" y1="4" x2="56" y2="60" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FF7A1A" />
          <stop offset="100%" stopColor="#FF4D00" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill={`url(#${gid})`} />
      <g fill="none" stroke="#fff" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M23 21V43" />
        <path d="M23 21H42" />
        <path d="M23 32H39" />
        <path d="M23 43H42" />
      </g>
      <circle cx="47" cy="32" r="4.5" fill="#fff" />
    </svg>
  );
}

export function Logo({
  variant = "lockup",
  size = 32,
  theme = "dark",
  compact = false,
  className,
}: Props) {
  const gid = useId();
  const ink = theme === "dark" ? "#FFFFFF" : "#0A0A0A";

  const mark = (
    <>
      <rect width="64" height="64" rx="16" fill={`url(#${gid})`} />
      <g fill="none" stroke="#fff" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M23 21V43" />
        <path d="M23 21H42" />
        <path d="M23 32H39" />
        <path d="M23 43H42" />
      </g>
      <circle cx="47" cy="32" r="4.5" fill="#fff" />
    </>
  );

  const defs = (
    <defs>
      <linearGradient id={gid} x1="8" y1="4" x2="56" y2="60" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#FF7A1A" />
        <stop offset="100%" stopColor="#FF4D00" />
      </linearGradient>
    </defs>
  );

  if (variant === "mark" || compact) {
    return (
      <svg
        viewBox="0 0 64 64"
        width={size}
        height={size}
        role="img"
        aria-label="EPI"
        className={className}
      >
        {defs}
        {mark}
      </svg>
    );
  }

  return (
    <svg
      viewBox="0 0 90 34"
      height={size}
      width={(size * 90) / 34}
      role="img"
      aria-label="EPI"
      className={className}
    >
      {defs}
      <g transform="scale(0.53125)">{mark}</g>
      <g
        transform="translate(44 5.8) scale(0.68)"
        fill="none"
        stroke={ink}
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M3 3V31" />
        <path d="M3 3H20" />
        <path d="M3 17H17" />
        <path d="M3 31H20" />
        <path d="M34 31V3" />
        <path d="M34 3H43A7 7 0 0 1 43 17H34" />
        <path d="M62 3V31" />
      </g>
    </svg>
  );
}
