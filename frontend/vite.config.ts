import path from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

const rootDirectory = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, rootDirectory, "");

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(rootDirectory, "src"),
      },
    },
    server: {
      host: "0.0.0.0",
      proxy: {
        "/api": {
          target: environment.VITE_API_PROXY_TARGET || "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
      restoreMocks: true,
    },
  };
});
