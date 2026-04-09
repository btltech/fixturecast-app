import "./app.css";
import App from "./App.svelte";
import { setupI18n } from "./lib/i18n";

// Initialize internationalization and then mount app
setupI18n().then(() => {
  const app = new App({
    target: document.getElementById("app"),
  });
});

export default {};
