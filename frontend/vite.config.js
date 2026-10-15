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
  },
});
