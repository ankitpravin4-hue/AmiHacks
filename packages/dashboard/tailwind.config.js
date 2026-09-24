/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#12141a",
          900: "#181b22",
          800: "#1e222b",
          700: "#272b36",
        },
        line: "#2d3340",
        inktext: {
          DEFAULT: "#eceef2",
          muted: "#9aa3b2",
          faint: "#6b7384",
        },
        accent: {
          DEFAULT: "#6b8cff",
          dim: "#4d6ad6",
        },
        critical: "#e5484d",
        high: "#e67a2e",
        medium: "#d4a017",
        low: "#8b93a7",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        "2xs": ["11px", { lineHeight: "16px" }],
        hero: ["72px", { lineHeight: "1", letterSpacing: "-0.03em", fontWeight: "700" }],
      },
      borderRadius: {
        card: "10px",
      },
      boxShadow: {
        card: "0 1px 0 rgba(255,255,255,0.04), 0 8px 24px rgba(0,0,0,0.24)",
        glow: "none",
      },
      spacing: {
        18: "4.5rem",
      },
    },
  },
  plugins: [],
};
