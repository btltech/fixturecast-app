import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
  },
  build: {
    chunkSizeWarningLimit: 1200,
    // Minification and obfuscation settings
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true,
        pure_funcs: ["console.log", "console.info", "console.debug"],
      },
      mangle: {
        toplevel: true, // Mangle top-level names
        properties: {
          regex: /^_/, // Mangle properties starting with underscore
        },
      },
      format: {
        comments: false, // Remove all comments
      },
    },
    // Chunk splitting for better caching
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return;

          const after = id.split("node_modules/")[1] || "";
          const parts = after.split("/");
          const pkg = parts[0]?.startsWith("@");
          const pkgName = pkg ? `${parts[0]}/${parts[1]}` : parts[0];
          if (!pkgName) return "vendor";

          // Keep Svelte-related deps together for better runtime locality.
          if (pkgName === "svelte" || pkgName === "svelte-routing")
            return "vendor_svelte";

          return `vendor_${pkgName.replace("@", "").replace("/", "_")}`;
        },
        // Obfuscate chunk names
        chunkFileNames: "assets/[hash].js",
        entryFileNames: "assets/[hash].js",
        assetFileNames: "assets/[hash].[ext]",
      },
    },
    // Enable source maps in production for better error tracking
    sourcemap: false, // Set to true if you need debugging
    // Optimize CSS
    cssCodeSplit: true,
  },
  // Optimize dependencies
  optimizeDeps: {
    include: ["svelte", "svelte-routing", "svelte-i18n"],
  },
});
