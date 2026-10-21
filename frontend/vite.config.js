import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The existing C4 plain-HTML dashboard lives at frontend/index.html.
// Keep it untouched: the new Vite app uses frontend/src/index.html instead.
export default defineConfig({
  root: fileURLToPath(new URL("./src/", import.meta.url)),
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "../dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // Keep the optional renderer separate from the farm UI and Three core.
        // No Three module is imported by the application entry point.
        manualChunks(id) {
          const module = id.replace(/\\/g, "/");
          if (module.includes("/three/build/three.core.js")) return "farm-three-core";
          if (module.includes("/three/build/three.module.js")) return "farm-webgl";
        },
      },
    },
  },
});
