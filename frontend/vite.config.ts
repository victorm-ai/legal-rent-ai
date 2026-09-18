/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    clearMocks: true,
    globals: true,
  },
  server: {
    port: 3000,
    watch: {
      // Dropbox sync touches many files at once; ignore its metadata paths.
      ignored: ['**/.dropbox/**', '**/.dropbox.cache/**'],
    },
  },
});
