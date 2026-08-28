import type { Config } from "tailwindcss";

// Design tokens — see DESIGN.md for the full rationale.
// Palette: deep instrument-panel navy, not pure black; one confident
// signal-blue accent; mint/amber/rose reserved exclusively for match
// score tiers (high/medium/low) so color always means the same thing.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "#0B0E14",
        surface: "#12161F",
        "surface-raised": "#1A2030",
        border: "#242B3D",
        "text-primary": "#E7EAF0",
        "text-secondary": "#8891A6",
        "text-muted": "#5B6478",
        signal: "#5B8CFF",
        "signal-dim": "#2E3F73",
        high: "#3DDC97",
        medium: "#F5A623",
        low: "#FF5C7A",
      },
      fontFamily: {
        display: ["var(--font-space-grotesk)", "sans-serif"],
        body: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px -12px rgba(0,0,0,0.6)",
      },
      borderRadius: {
        card: "14px",
      },
    },
  },
  plugins: [],
};

export default config;
