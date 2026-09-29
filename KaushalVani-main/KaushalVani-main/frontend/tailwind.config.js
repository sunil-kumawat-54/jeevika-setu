/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        govBlue: {
          50: '#f0f4f9',
          100: '#d9e2ec',
          600: '#1e3a8a',
          700: '#0f294a',
          800: '#0b1d36',
        },
        govGreen: {
          600: '#15803d',
          700: '#166534',
        },
        govText: '#1f2937',
        govBg: '#f8fafc',
      },
      fontFamily: {
        sans: ['Noto Sans', 'Noto Sans Devanagari', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
