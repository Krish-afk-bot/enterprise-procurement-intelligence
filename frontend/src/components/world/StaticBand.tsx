/**
 * The written band.
 *
 * Shown when the workspace cannot, or will not, draw WebGL: no graphics context,
 * a phone, the static quality tier, or a failure in the 3D layer. It is not a
 * placeholder and never an empty rectangle — the Watcher, the Courier and the
 * paper lanes are all here as SVG, with the same real collection name on the
 * suitcase.
 *
 * It is decorative and marked as such; the two settings that change the 3D band
 * change this one too, so a reader who hides the buddy is not handed a drawing
 * of the buddy instead.
 */

/** Paper sheets parked along the lanes, at fixed positions: nothing moves. */
const SHEETS: Array<{ left: string; top: string; rotate: number; tint: string }> = [
  { left: "14%", top: "14%", rotate: -9, tint: "hsl(var(--primary) / 0.35)" },
  { left: "31%", top: "56%", rotate: 7, tint: "hsl(var(--success) / 0.32)" },
  { left: "49%", top: "20%", rotate: -5, tint: "hsl(var(--warning) / 0.34)" },
  { left: "66%", top: "62%", rotate: 11, tint: "hsl(var(--info) / 0.3)" },
  { left: "83%", top: "26%", rotate: -7, tint: "hsl(var(--muted-foreground) / 0.22)" },
];

export function StaticBand({ label, hideBuddy }: { label: string; hideBuddy: boolean }) {
  return (
    <div
      className="relative h-full w-full overflow-hidden rounded-lg border bg-[hsl(var(--paper))]"
      aria-hidden="true"
    >
      {/* The lanes: Supplier → Contract → Product → Price → Evidence. */}
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
        <path
          d="M0,26 C22,8 44,44 66,24 S90,38 100,26"
          fill="none"
          stroke="hsl(var(--foreground) / 0.22)"
          strokeWidth="0.6"
          strokeDasharray="2 2"
          vectorEffect="non-scaling-stroke"
        />
        <path
          d="M0,58 C24,40 46,74 68,56 S92,68 100,58"
          fill="none"
          stroke="hsl(var(--foreground) / 0.16)"
          strokeWidth="0.6"
          strokeDasharray="2 2"
          vectorEffect="non-scaling-stroke"
        />
      </svg>

      {SHEETS.map((sheet) => (
        <span
          key={sheet.left}
          className="absolute block h-5 w-4 rounded-[3px] border border-foreground/20"
          style={{ left: sheet.left, top: sheet.top, background: sheet.tint, transform: `rotate(${sheet.rotate}deg)` }}
        />
      ))}

      {hideBuddy ? null : (
        <>
          {/* The Watcher, still watching, just not moving. */}
          <svg
            className="absolute bottom-0 left-3 h-[86%] w-auto"
            viewBox="0 0 96 96"
            fill="none"
            aria-hidden="true"
          >
            <rect x="25" y="62" width="46" height="34" rx="12" fill="hsl(var(--primary))" />
            <circle cx="48" cy="42" r="30" fill="hsl(var(--paper))" stroke="hsl(var(--foreground) / 0.35)" />
            <ellipse cx="37" cy="40" rx="10" ry="10" fill="hsl(var(--foreground))" />
            <ellipse cx="59" cy="40" rx="10" ry="10" fill="hsl(var(--foreground))" />
            <circle cx="38.5" cy="41" r="4" fill="hsl(var(--paper))" />
            <circle cx="60.5" cy="41" r="4" fill="hsl(var(--paper))" />
            <rect x="27" y="23" width="15" height="3.5" rx="1.75" fill="hsl(var(--foreground))" />
            <rect x="54" y="23" width="15" height="3.5" rx="1.75" fill="hsl(var(--foreground))" />
            <rect x="40" y="55" width="16" height="3.5" rx="1.75" fill="hsl(var(--foreground))" />
            <circle cx="24" cy="50" r="6" fill="hsl(var(--coral) / 0.5)" />
            <circle cx="72" cy="50" r="6" fill="hsl(var(--coral) / 0.5)" />
          </svg>

          {/* The Courier, standing still with the folder for this page. */}
          <div className="absolute bottom-1 right-4 flex items-end gap-2">
            <span className="rounded border border-foreground/25 bg-background/95 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-foreground">
              {label}
            </span>
            <svg className="h-[80%] w-auto" viewBox="0 0 54 84" fill="none" aria-hidden="true">
              <rect x="14" y="74" width="9" height="10" rx="3" fill="hsl(var(--foreground))" />
              <rect x="30" y="74" width="9" height="10" rx="3" fill="hsl(var(--foreground))" />
              <rect x="11" y="34" width="31" height="30" rx="9" fill="hsl(var(--primary))" />
              <circle cx="27" cy="22" r="13" fill="hsl(var(--paper))" stroke="hsl(var(--foreground) / 0.35)" />
              <ellipse cx="27" cy="8" rx="18" ry="3.5" fill="hsl(var(--warm))" />
              <rect x="18" y="1" width="18" height="8" rx="4" fill="hsl(var(--warm))" />
              <rect x="36" y="52" width="18" height="15" rx="3" fill="hsl(var(--warm))" stroke="hsl(var(--foreground) / 0.4)" />
            </svg>
          </div>
        </>
      )}
    </div>
  );
}
