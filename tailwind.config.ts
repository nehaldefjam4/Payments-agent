import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        fam: {
          black: "#000000",
          dark: "#1a1a1a",
          darker: "#111111",
          gray: "#333333",
          "gray-light": "#666666",
          "gray-lighter": "#999999",
          orange: "#FF8562",
          "orange-light": "#FF9E80",
          white: "#FFFFFF",
          "off-white": "#F5F5F5",
        },
        success: "#22c55e",
        warning: "#f59e0b",
        danger: "#ef4444",
      },
      fontFamily: {
        sans: ['"Public Sans"', "Arial", "sans-serif"],
      },
      borderRadius: {
        pill: "100px",
      },
    },
  },
  plugins: [],
};
export default config;
