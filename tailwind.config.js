/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["**/*.py"],
  theme: {
    colors: {
      "ivory-light": "#faf9f5",
      "ivory-medium": "#f0eee6",
      "ivory-dark": "#e8e6dc",
      "cloud-light": "#d1cfc5",
      "cloud-medium": "#b0aea5",
      "cloud-dark": "#87867f",
      leather: "#cc785c",
      sky: "#6a9bcc",
      olive: "#788c5d",
      kraft: "#d4a27f",
      clay: "#d97757",
      coral: "#ebcece",
      cactus: "#bcd1ca",
      oat: "#e3dacc",
      fig: "#c46686",
      dark: "#0f0f0e",
      white: "#ffffff",
    },
    borderRadius: {
      material: "12px",
      card: "16px",
    },
    fontFamily: {
      sans: ["Merriweather", "serif"],
      heading: ["Poppins", "sans-serif"],
    },
  },
};
