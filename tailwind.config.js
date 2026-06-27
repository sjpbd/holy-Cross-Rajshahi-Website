/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.js"
  ],
  theme: {
    extend: {
        colors: {
            'primary': '#1e3a8a',      // Navy Blue
            'primary-dark': '#1c2a4e',
            'primary-light': '#3b82f6',
            'accent': '#d4af37',       // Metallic Gold
            'accent-dark': '#b8941e',
            'accent-light': '#f4d03f',
            'footer-text': '#E5E7EB', // Light Gray
        }
    }
  },
  plugins: [],
}
