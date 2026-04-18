import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        spectra: {
          primary:   "#6B5CE7", // Purple (main theme)
          secondary: "#6B5CE7", // Purple (consistent)
          dark:      "#030305",
          surface:   "#0F0E17",
          text:      "#FAFAFA",
          muted:     "#8C8C99",
          bg:        "#050508",
        },
      },
      keyframes: {
        // Soft pulse for idle orb
        "orb-idle": {
          "0%, 100%": { transform: "scale(1)",    opacity: "0.7" },
          "50%":      { transform: "scale(1.06)", opacity: "1"   },
        },
        // Intense pulse for active listening
        "orb-listen": {
          "0%, 100%": { transform: "scale(1)",    boxShadow: "0 0 0 0 rgba(0, 229, 255, 0.5)" },
          "50%":      { transform: "scale(1.1)",  boxShadow: "0 0 0 28px rgba(0, 229, 255, 0)" },
        },
        // Orb pulse for Spectra speaking
        "orb-speak": {
          "0%, 100%": { transform: "scale(1)",    boxShadow: "0 0 0 0 rgba(176, 38, 255, 0.5)" },
          "50%":      { transform: "scale(1.12)", boxShadow: "0 0 0 28px rgba(176, 38, 255, 0)" },
        },
        // Waveform bar (staggered by delay)
        wave: {
          "0%, 100%": { transform: "scaleY(0.25)" },
          "50%":      { transform: "scaleY(1)"    },
        },
        // Slide-in for new messages
        "slide-up": {
          "0%":   { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)"    },
        },
        "fade-in": {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },
      animation: {
        "orb-idle":   "orb-idle 3s ease-in-out infinite",
        "orb-listen": "orb-listen 1.1s ease-in-out infinite",
        "orb-speak":  "orb-speak 0.9s ease-in-out infinite",
        "wave-1":     "wave 0.9s ease-in-out 0.00s infinite",
        "wave-2":     "wave 0.9s ease-in-out 0.12s infinite",
        "wave-3":     "wave 0.9s ease-in-out 0.24s infinite",
        "wave-4":     "wave 0.9s ease-in-out 0.36s infinite",
        "wave-5":     "wave 0.9s ease-in-out 0.48s infinite",
        "slide-up":   "slide-up 0.2s ease-out both",
        "fade-in":    "fade-in 0.25s ease-out both",
      },
    },
  },
  plugins: [],
};
export default config;
