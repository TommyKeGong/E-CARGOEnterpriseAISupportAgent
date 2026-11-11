import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#17202a',
        paper: '#f7f5ef',
        signal: '#0d7665',
        amber: '#c06b24',
      },
    },
  },
  plugins: [],
} satisfies Config
