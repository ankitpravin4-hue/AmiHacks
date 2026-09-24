import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    host: "127.0.0.1",
    proxy: {
      "/scans": {
        target: "http://127.0.0.1:8100",
        changeOrigin: true,
        ws: true,
        bypass(req) {
          if (req.headers.accept?.includes("text/html")) return "/index.html";
        },
      },
      "/healthz": { target: "http://127.0.0.1:8100", changeOrigin: true },
    },
  },
});
