import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    // three.js, its React renderer and its helpers must all see the same single
    // copy of React. Without this Vite pre-bundles a second instance for the 3D
    // chunks and every hook inside <Canvas> fails with "Invalid hook call".
    dedupe: ["react", "react-dom", "three"],
  },
  optimizeDeps: {
    include: ["three", "@react-three/fiber", "@react-three/drei"],
  },
  server: {
    port: 5173,
    strictPort: false,
    // The API is proxied so the browser only ever talks to one origin in dev.
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
