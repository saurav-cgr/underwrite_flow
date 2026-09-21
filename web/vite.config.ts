import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://api:8000",
    },
  },
  test: {
    testTimeout: 10_000,
  },
});
