/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Fondo base estilo terminal
        bg: {
          950: '#05080f',
          900: '#0a0f1a',
          800: '#0f1626',
          700: '#16203a',
        },
        // Verde matrix / hacker
        primary: {
          50: '#e6fff0',
          100: '#c8ffdf',
          200: '#94f7bd',
          300: '#5ce89a',
          400: '#2fd67c',
          500: '#00ff41',
          600: '#00cc34',
          700: '#009e2a',
          800: '#007a21',
          900: '#005918',
        },
        // Cyan neón para acentos
        neon: {
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#00d9ff',
          600: '#00b8d4',
        },
        // Rojo alerta
        alert: {
          400: '#ff5555',
          500: '#ff2e2e',
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', 'Consolas', 'Menlo', 'monospace'],
      },
      boxShadow: {
        'neon': '0 0 5px rgba(0, 255, 65, 0.3), 0 0 15px rgba(0, 255, 65, 0.1)',
        'neon-cyan': '0 0 5px rgba(0, 217, 255, 0.3), 0 0 15px rgba(0, 217, 255, 0.1)',
        'neon-red': '0 0 5px rgba(255, 46, 46, 0.4), 0 0 15px rgba(255, 46, 46, 0.15)',
      },
    },
  },
  plugins: [],
}
