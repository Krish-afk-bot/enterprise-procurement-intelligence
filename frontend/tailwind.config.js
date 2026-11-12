/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        success: "hsl(var(--success))",
        warning: "hsl(var(--warning))",
        info: "hsl(var(--info))",
        // Metadata below body copy: #71717A.
        subtle: "hsl(var(--subtle))",
        // Playful accents for the optional 3D world only.
        warm: {
          DEFAULT: "hsl(var(--warm))",
          foreground: "hsl(var(--warm-foreground))",
        },
        coral: {
          DEFAULT: "hsl(var(--coral))",
          foreground: "hsl(var(--coral-foreground))",
        },
        paper: "hsl(var(--paper))",
        // The three ground tones of the monochrome system.
        ink: {
          DEFAULT: "#050505",
          2: "#0A0A0A",
          3: "#111111",
          4: "#171717",
        },
      },
      fontFamily: {
        sans: [
          "Inter var",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        display: [
          "Inter var",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "SF Mono", "Menlo", "Consolas", "Liberation Mono", "monospace"],
      },
      fontSize: {
        // Display sizes used by the landing page and page titles.
        display: ["clamp(2.75rem, 6vw, 5.25rem)", { lineHeight: "0.98", letterSpacing: "-0.035em", fontWeight: "600" }],
        "display-sm": ["clamp(2rem, 3.6vw, 3.25rem)", { lineHeight: "1.04", letterSpacing: "-0.03em", fontWeight: "600" }],
        section: ["clamp(1.5rem, 2.4vw, 2.25rem)", { lineHeight: "1.12", letterSpacing: "-0.025em", fontWeight: "600" }],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 3px)",
        sm: "calc(var(--radius) - 5px)",
        xl: "calc(var(--radius) + 4px)",
      },
      boxShadow: {
        overlay: "0 24px 64px -24px rgb(0 0 0 / 0.85)",
        // A white inner hairline plus a deep drop: the "premium card" edge.
        card: "inset 0 1px 0 0 rgb(255 255 255 / 0.05), 0 20px 50px -40px rgb(0 0 0 / 0.95)",
        glow: "0 0 0 1px rgb(255 255 255 / 0.10), 0 12px 40px -12px rgb(255 255 255 / 0.22)",
        "glow-lg": "0 0 0 1px rgb(255 255 255 / 0.16), 0 24px 70px -18px rgb(255 255 255 / 0.3)",
      },
      transitionDuration: {
        micro: "120ms",
        control: "180ms",
        panel: "240ms",
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        shimmer: "shimmer 2.4s linear infinite",
      },
    },
  },
  plugins: [],
};
