import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  base: "/urbanisme95/",
  plugins: [react()],
  resolve: {
    alias: {
      "next/link": resolve(__dirname, "app/components/StaticLink.tsx"),
    },
  },
  build: {
    outDir: "dist-github",
    emptyOutDir: true,
  },
});
