import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17201c",
        moss: "#2f6f4e",
        mint: "#dff7ea",
        clay: "#b66745",
        skyglass: "#e8f2ff"
      },
      boxShadow: {
        soft: "0 18px 50px rgba(23, 32, 28, 0.10)"
      }
    }
  },
  plugins: []
} satisfies Config;
