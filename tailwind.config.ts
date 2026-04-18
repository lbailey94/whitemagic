import type { Config } from "tailwindcss";

/**
 * Design tokens ported from whitemagic-frontend/web/index.css.
 * Light mode: warm cream paper + lavender ink.
 * Dark mode:  warm ink + luminous lavender.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx,mdx}",
    "./components/**/*.{ts,tsx,mdx}",
    "./content/**/*.{md,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "var(--bg-color)",
        surface: "var(--surface)",
        "surface-alt": "var(--surface-alt)",
        ink: "var(--ink)",
        fg: "var(--text-color)",
        muted: "var(--text-muted)",
        dim: "var(--dim-text)",
        border: "var(--border)",
        "border-light": "var(--border-light)",
        lavender: {
          DEFAULT: "var(--lavender)",
          light: "var(--lavender-light)",
          dark: "var(--lavender-dark)",
          bg: "var(--lavender-bg)",
        },
      },
      fontFamily: {
        head: ["var(--font-head)"],
        body: ["var(--font-body)"],
        zh: ["var(--font-zh)"],
        mono: ["var(--font-mono)"],
      },
      maxWidth: {
        prose: "68ch",
        site: "1200px",
      },
    },
  },
  plugins: [],
};

export default config;
