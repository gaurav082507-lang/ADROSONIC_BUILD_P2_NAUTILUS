/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: '#0B1220',
        navy: '#0F1B2D',
        background: '#F5F7FA',
        card: '#FFFFFF',
        border: '#E3E8EF',
        muted: '#5B6B82',
        accent: '#F5C518',
        primary: '#3B82F6',
        band: {
          low: '#16A34A',
          medium: '#D97706',
          high: '#DC2626'
        }
      },
      fontFamily: {
        heading: ['"Space Grotesk"', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        card: '12px',
        control: '8px',
      },
      boxShadow: {
        soft: '0 1px 3px 0 rgba(11, 18, 32, 0.05), 0 1px 2px -1px rgba(11, 18, 32, 0.05)',
        card: '0 4px 6px -1px rgba(11, 18, 32, 0.07), 0 2px 4px -2px rgba(11, 18, 32, 0.05)',
      }
    },
  },
  plugins: [],
}
