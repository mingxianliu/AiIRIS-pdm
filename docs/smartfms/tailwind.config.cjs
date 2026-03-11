/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "fms-bg": "#0B0F14",
        "fms-panel": "#111922",
        "fms-panel-2": "#0F151C",
        "fms-border": "#1F2B3B",
        "fms-accent": "#74E9DB",
        "fms-accent-2": "#2EE6A6",
        "fms-warn": "#F2B84B",
        "fms-info": "#4DB8FF"
      },
      fontFamily: {
        display: ["Space Grotesk", "system-ui", "sans-serif"],
        body: ["IBM Plex Sans", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};
