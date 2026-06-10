import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/adjudicate":   "http://localhost:8000",
      "/generate_spec":"http://localhost:8000",
      "/health":       "http://localhost:8000",
      "/status":       "http://localhost:8000",
      "/.well-known":  "http://localhost:8000",
      "/spec":         "http://localhost:8000",
    },
  },
  define: {
    __SERVICE_URL__: JSON.stringify(process.env.VITE_SERVICE_URL || ""),
  },
});
