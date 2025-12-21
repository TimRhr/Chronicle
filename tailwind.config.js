/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./src/templates/**/*.html",
    "./src/static/js/**/*.js",
  ],
  theme: {
    extend: {

      /* -------------------------------------------------
         Color System (Light & Dark)
         ------------------------------------------------- */

      colors: {
        brand: {
          mint: "#bcd9c6",
          teal: "#4da9a4",
          blue: "#4081a4",
          violet: "#4f4191",
          plum: "#592d80",
        },

        /* Light Mode Tokens */
        light: {
          bg: "#f7faf8",
          surface: "#ffffff",
          text: {
            primary: "#1f2933",
            secondary: "#4b5563",
            muted: "#6b7280",
          },
          border: "#e5e7eb",
        },

        /* Dark Mode Tokens */
        dark: {
          bg: "#0f1220",
          surface: "#171a2d",
          text: {
            primary: "#e5e7eb",
            secondary: "#b6bcc9",
            muted: "#8b91a1",
          },
          border: "#2a2f45",
        },

        /* Dim Mode Tokens (warm intermediate) */
        dim: {
          bg: "#1a1d2e",
          surface: "#242838",
          text: {
            primary: "#d4d8e0",
            secondary: "#a0a8b8",
            muted: "#7a8294",
          },
          border: "#363d52",
        },
      },

      /* -------------------------------------------------
         Typography
         ------------------------------------------------- */

      fontFamily: {
        heading: ["Merriweather", "serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },

      /* -------------------------------------------------
         Layout & Radius
         ------------------------------------------------- */

      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
        xl: "24px",
      },

      /* -------------------------------------------------
         Shadows (Soft, Editorial)
         ------------------------------------------------- */

      boxShadow: {
        card: "0 6px 24px rgba(0,0,0,0.06)",
        "card-dark": "0 6px 24px rgba(0,0,0,0.4)",
      },

      /* -------------------------------------------------
         Background Gradients
         ------------------------------------------------- */

      backgroundImage: {
        "brand-soft":
          "linear-gradient(135deg, #bcd9c6 0%, #4da9a4 100%)",
        "brand-accent":
          "linear-gradient(135deg, #4f4191 0%, #592d80 100%)",
      },
    },
  },
  plugins: [
    require("@tailwindcss/typography"),
  ],
};
