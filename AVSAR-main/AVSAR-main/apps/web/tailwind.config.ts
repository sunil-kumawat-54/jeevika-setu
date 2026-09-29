import type { Config } from 'tailwindcss';

/**
 * AVSAR design tokens.
 * Accessibility contract (RULE 7 / research.md §9.5):
 *  - tap targets >= 24px (WCAG 2.2 §2.5.8); our `.tap` utility uses 56px.
 *  - Devanagari is a "tall script": line-height +0.1em vs Latin, Noto Sans, never Bold.
 *  - light + dark themes, both contrast-checked against WCAG 2.2 AA (4.5:1 body text).
 */
const config: Config = {
  darkMode: 'class',
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Brand — indigo/saffron pairing, both AA on their paired surfaces.
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
        accent: {
          400: '#fb923c',
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
        },
        ink: {
          DEFAULT: '#111827',
          soft: '#374151',
          muted: '#4b5563',
        },
        surface: {
          DEFAULT: '#ffffff',
          sunken: '#f5f6fa',
          raised: '#ffffff',
        },
        ok: { 500: '#15803d', 100: '#dcfce7' },
        warn: { 500: '#b45309', 100: '#fef3c7' },
        danger: { 500: '#b91c1c', 100: '#fee2e2' },
        synthetic: { 500: '#7c3aed', 100: '#ede9fe' },
      },
      fontFamily: {
        sans: ['"Noto Sans"', '"Noto Sans Devanagari"', '"Noto Sans Telugu"', 'system-ui', 'sans-serif'],
      },
      lineHeight: {
        // Devanagari matras/shirorekha need generous leading (research.md §9.5).
        indic: '1.75',
      },
      borderRadius: { xl2: '1.25rem' },
      minHeight: { tap: '3.5rem' },
      minWidth: { tap: '3.5rem' },
      boxShadow: {
        focus: '0 0 0 3px #ffffff, 0 0 0 6px #4f46e5',
      },
    },
  },
  plugins: [],
};

export default config;
