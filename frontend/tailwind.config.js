/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Custom colors for entity highlighting
        entity: {
          phone: {
            50: '#eff6ff',
            100: '#dbeafe',
            300: '#93c5fd',
            800: '#1e40af'
          },
          email: {
            50: '#f0fdf4',
            100: '#dcfce7',
            300: '#86efac',
            800: '#166534'
          },
          crypto: {
            50: '#fefce8',
            100: '#fef3c7',
            300: '#fcd34d',
            900: '#78350f'
          },
          url: {
            50: '#faf5ff',
            100: '#f3e8ff',
            300: '#c4b5fd',
            800: '#5b21b6'
          }
        }
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Consolas', 'monospace'],
      }
    },
  },
  plugins: [],
}