/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#07090d",
          900: "#0b1018",
          800: "#111827",
          700: "#1a2332",
        },
        line: "#1e2a3a",
        critical: "#f43f5e",
        high: "#f97316",
        medium: "#f59e0b",
        low: "#94a3b8",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        glow: "0 0 40px rgba(14, 165, 233, 0.08)",
      },
    },
  },
  plugins: [],
};
