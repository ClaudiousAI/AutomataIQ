import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite config for the SAIE front-end.
//
// M01 keeps the build surface minimal: a single SPA, a /health JSON
// proxied to the API, and a sensible split of dev vs production
// output. M02+ will add the OIDC client and richer routing.
//
// Traceability: NFR-005 (the dev server proxies /health to the API
// so the UI can display the backend status), NFR-006 (typed env
// contract via VITE_*-prefixed variables).

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // During `vite dev`, route /api/* to the FastAPI container so the
    // SPA talks to the real backend without CORS gymnastics.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
  },
});
