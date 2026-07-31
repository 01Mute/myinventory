import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // Bind mounts on Windows and macOS do not forward file system events into
    // the container, so Vite never sees edits and keeps serving the module it
    // transformed at startup. Polling costs a little CPU and is the only way
    // to make hot reload work without restarting the container.
    watch: {
      usePolling: true,
      interval: 300
    }
  }
});
