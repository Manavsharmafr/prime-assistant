/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        prime: {
          dark: "#0a0b0d",
          panel: "#12141c",
          border: "#1f2233",
          cyan: "#00f0ff",
          purple: "#bd00ff",
          glow: "rgba(0, 240, 255, 0.15)",
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s infinite ease-in-out',
        'rotate-slow': 'rotateSlow 8s infinite linear',
        'pulse-slow': 'pulseSlow 3s infinite ease-in-out',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { transform: 'scale(1)', filter: 'drop-shadow(0 0 10px rgba(0, 240, 255, 0.4))' },
          '50%': { transform: 'scale(1.05)', filter: 'drop-shadow(0 0 25px rgba(0, 240, 255, 0.8))' },
        },
        rotateSlow: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        pulseSlow: {
          '0%, 100%': { opacity: '0.3' },
          '50%': { opacity: '0.8' },
        }
      }
    },
  },
  plugins: [],
}
