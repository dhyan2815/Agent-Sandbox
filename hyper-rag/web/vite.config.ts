import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API runs separately (uvicorn on :8000) and Vite forwards these paths
// to it, so the page and the API share one origin and the login cookie works unchanged.
const API = ["/config", "/packs", "/ask", "/collections", "/login", "/logout", "/health"];

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(API.map((path) => [path, "http://127.0.0.1:8000"])),
  },
});
