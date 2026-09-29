import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ["web"],
    proxy: {
      "/api": "http://api:8000",
    },
  },
  test: {
    exclude: ["e2e/**", "**/node_modules/**"],
    testTimeout: 10_000,
  },
});
