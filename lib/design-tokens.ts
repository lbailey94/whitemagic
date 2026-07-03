/**
 * WhiteMagic Labs — Design Tokens v1.0.0
 *
 * Canonical source of truth for all brand values.
 * Consumed by Tailwind config (tailwind.config.ts), components, and MDX layouts.
 * Dark/light variants correspond to CSS custom properties in globals.css.
 */

export const tokens = {
  colors: {
    light: {
      bg: "#faf7f2",
      surface: "#ffffff",
      "surface-alt": "#f3efe8",
      ink: "#2d2a26",
      fg: "#3d3a36",
      muted: "#6b6560",
      dim: "#9a938c",
      border: "#e0dbd4",
      "border-light": "#ede8e1",
      lavender: "#6b5b9a",
      "lavender-light": "#8b7dba",
      "lavender-dark": "#4b3d6a",
      "lavender-bg": "#f0ecf7",
    },
    dark: {
      bg: "#1a1816",
      surface: "#242220",
      "surface-alt": "#2e2c28",
      ink: "#ede8e1",
      fg: "#d4cfc8",
      muted: "#9a938c",
      dim: "#6b6560",
      border: "#3d3a36",
      "border-light": "#2e2c28",
      lavender: "#a08cd8",
      "lavender-light": "#b8a4ea",
      "lavender-dark": "#7b6baa",
      "lavender-bg": "#2a2638",
    },
  },

  typography: {
    head: "'Plus Jakarta Sans', sans-serif",
    body: "'Charter', 'Georgia', serif",
    zh: "'Noto Serif SC', serif",
    mono: "'JetBrains Mono', 'Fira Code', monospace",
    sizes: {
      xs: "0.75rem",
      sm: "0.875rem",
      base: "1rem",
      lg: "1.125rem",
      xl: "1.25rem",
      "2xl": "1.5rem",
      "3xl": "1.875rem",
      "4xl": "2.25rem",
    },
    weights: {
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
  },

  spacing: {
    xs: "0.25rem",
    sm: "0.5rem",
    md: "1rem",
    lg: "1.5rem",
    xl: "2rem",
    "2xl": "3rem",
    "3xl": "4rem",
    "4xl": "6rem",
  },

  radii: {
    sm: "0.25rem",
    md: "0.5rem",
    lg: "0.75rem",
    xl: "1rem",
    full: "9999px",
  },

  shadows: {
    sm: "0 1px 2px rgba(0,0,0,0.05)",
    md: "0 4px 6px rgba(0,0,0,0.07)",
    lg: "0 10px 25px rgba(0,0,0,0.1)",
  },

  layout: {
    prose: "68ch",
    site: "1200px",
    nav: "64px",
  },
} as const;

export const epistemicColors = {
  Proven: { bg: "#d4edda", fg: "#155724", hex: "#28a745" },
  Promising: { bg: "#d1ecf1", fg: "#0c5460", hex: "#17a2b8" },
  Contested: { bg: "#fff3cd", fg: "#856404", hex: "#ffc107" },
  Speculative: { bg: "#f8d7da", fg: "#721c24", hex: "#dc3545" },
  Mythopoetic: { bg: "#e8daef", fg: "#4a235a", hex: "#8e44ad" },
} as const;

export type EpistemicTag = keyof typeof epistemicColors;
