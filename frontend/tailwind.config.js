/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        forest: "#123C2D",
        deep: "#1B513C",
        sage: "#E8F2E9",
        pale: "#D0E5CE",
        muted: "#64748B",
        alert: "#DC2626",
        warning: "#F59E0B",
      },
      fontFamily: {
        sans: ["Times New Roman", "Times", "serif"],
        display: ["Times New Roman", "Times", "serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(18, 60, 45, 0.06), 0 8px 24px rgba(18, 60, 45, 0.04)",
      },
    },
  },
  plugins: [],
};
