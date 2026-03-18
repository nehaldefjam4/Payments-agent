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
        primary: {
          DEFAULT: "#1a1a2e",
          light: "#16213e",
          dark: "#0f0f1e",
        },
        accent: {
          DEFAULT: "#e94560",
          light: "#ff6b81",
          dark: "#c23152",
        },
        success: "#00b894",
        warning: "#fdcb6e",
        danger: "#d63031",
      },
    },
  },
  plugins: [],
};
export default config;
