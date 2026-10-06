/**
 * Scene colours come from the same design tokens as the rest of the product, so
 * a 3D surface can never introduce a second brand colour. Tokens are stored as
 * `H S% L%` triples; three.js needs a concrete colour, so they are converted
 * once and cached.
 */

interface Hsl {
  h: number;
  s: number;
  l: number;
}

function readToken(name: string, fallback: Hsl): Hsl {
  if (typeof window === "undefined") return fallback;
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const parts = raw.split(/\s+/).map((part) => Number.parseFloat(part));
  if (parts.length < 3 || parts.some((value) => Number.isNaN(value))) return fallback;
  return { h: parts[0], s: parts[1] / 100, l: parts[2] / 100 };
}

function hslToHex({ h, s, l }: Hsl): string {
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const hh = h / 60;
  const x = c * (1 - Math.abs((hh % 2) - 1));
  const [r1, g1, b1] =
    hh < 1
      ? [c, x, 0]
      : hh < 2
        ? [x, c, 0]
        : hh < 3
          ? [0, c, x]
          : hh < 4
            ? [0, x, c]
            : hh < 5
              ? [x, 0, c]
              : [c, 0, x];
  const m = l - c / 2;
  const toHex = (value: number) =>
    Math.round((value + m) * 255)
      .toString(16)
      .padStart(2, "0");
  return `#${toHex(r1)}${toHex(g1)}${toHex(b1)}`;
}

export interface ScenePalette {
  background: string;
  primary: string;
  foreground: string;
  muted: string;
  border: string;
  success: string;
  warning: string;
  info: string;
  /** Playful accents: warm yellow and coral, used only by the world layer. */
  warm: string;
  coral: string;
  /** Off-white paper tone, so characters match the page rather than glare. */
  paper: string;
}

let cached: ScenePalette | null = null;

export function scenePalette(): ScenePalette {
  if (cached) return cached;
  cached = {
    background: hslToHex(readToken("--background", { h: 0, s: 0, l: 1 })),
    primary: hslToHex(readToken("--primary", { h: 217, s: 0.71, l: 0.38 })),
    foreground: hslToHex(readToken("--foreground", { h: 222, s: 0.3, l: 0.12 })),
    muted: hslToHex(readToken("--muted", { h: 220, s: 0.16, l: 0.965 })),
    border: hslToHex(readToken("--border", { h: 220, s: 0.15, l: 0.9 })),
    success: hslToHex(readToken("--success", { h: 145, s: 0.58, l: 0.31 })),
    warning: hslToHex(readToken("--warning", { h: 32, s: 0.84, l: 0.36 })),
    info: hslToHex(readToken("--info", { h: 213, s: 0.74, l: 0.42 })),
    warm: hslToHex(readToken("--warm", { h: 42, s: 0.92, l: 0.55 })),
    coral: hslToHex(readToken("--coral", { h: 12, s: 0.84, l: 0.62 })),
    paper: hslToHex(readToken("--paper", { h: 40, s: 0.44, l: 0.97 })),
  };
  return cached;
}

/** Colour per entity label, drawn from the palette rather than invented. */
export function labelColour(label: string, palette: ScenePalette): string {
  switch (label) {
    case "Supplier":
      return palette.primary;
    case "Contract":
    case "Amendment":
      return palette.success;
    case "Product":
    case "Price":
      return palette.warning;
    case "ComplianceCertificate":
      return palette.foreground;
    default:
      return palette.muted;
  }
}
