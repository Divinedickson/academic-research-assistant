import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiBaseUrl = env.VITE_API_BASE_URL

  if (
    mode === 'production' &&
    (!apiBaseUrl || /localhost|127\.0\.0\.1/.test(apiBaseUrl))
  ) {
    throw new Error('A non-local VITE_API_BASE_URL is required for production builds.')
  }

  return {
    plugins: [react()],
  }
})
