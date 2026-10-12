import { fileURLToPath } from "node:url";
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/",
  build: {
    rollupOptions: {
      input: Object.fromEntries(["", "services", "approach", "pricing", "about", "contact"].map(page => [
        page || "home", fileURLToPath(new URL(`./${page ? page + "/" : ""}index.html`, import.meta.url)),
      ])),
    },
  },
})
