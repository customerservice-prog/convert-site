/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#0c1222", muted: "#64748b" },
        surface: { card: "#151b2e", border: "#2d3a52" },
      },
    },
  },
  plugins: [],
};
