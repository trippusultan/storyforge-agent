import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Base path. For the FastAPI gateway use "/ui/"; for Firebase Hosting (root)
// build with VITE_BASE=/
const BASE = process.env.VITE_BASE || '/ui/'

export default defineConfig({
  base: BASE,
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API calls to the FastAPI gateway during dev.
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
  },
})
