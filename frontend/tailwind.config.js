/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        studio: {
          bg: "var(--studio-bg)",
          surface: "var(--studio-surface)",
          surface2: "var(--studio-surface2)",
          border: "var(--studio-border)",
          text: "var(--studio-text)",
          muted: "var(--studio-muted)",
        },
        marquee: {
          DEFAULT: "#F2B84B",
          dim: "#C99A3E",
        },
        reel: {
          DEFAULT: "#FF5D73",
          dim: "#D9495F",
        },
        success: "#3DDC97",
        danger: "#FF6B6B",
      },
      fontFamily: {
        display: ["'Bricolage Grotesque'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(242, 184, 75, 0.35)",
        card: "0 8px 30px -12px rgba(0,0,0,0.45)",
      },
      keyframes: {
        sprocketPulse: {
          "0%, 100%": { opacity: 1, transform: "scale(1)" },
          "50%": { opacity: 0.6, transform: "scale(0.92)" },
        },
        filmScroll: {
          "0%": { backgroundPositionY: "0" },
          "100%": { backgroundPositionY: "80px" },
        },
      },
      animation: {
        sprocketPulse: "sprocketPulse 1.4s ease-in-out infinite",
        filmScroll: "filmScroll 4s linear infinite",
      },
    },
  },
  plugins: [],
};
