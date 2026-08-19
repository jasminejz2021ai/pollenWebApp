/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        pollen: {
          low: '#22c55e',
          moderate: '#facc15',
          high: '#f97316',
          'very-high': '#ef4444',
          extreme: '#991b1b',
        },
      },
    },
  },
  plugins: [],
};
