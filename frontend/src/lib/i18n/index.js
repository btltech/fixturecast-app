// i18n configuration for FixtureCast
import {
  register,
  init,
  getLocaleFromNavigator,
  locale,
  waitLocale,
} from "svelte-i18n";

// Register all locales
register("en", () => import("./en.json"));
register("es", () => import("./es.json"));
register("pt", () => import("./pt.json"));
register("fr", () => import("./fr.json"));

export const supportedLocales = ["en", "es", "pt", "fr"];

export function normalizeLocale(value) {
  if (!value) {
    return null;
  }

  const lowerValue = value.toLowerCase();
  if (supportedLocales.includes(lowerValue)) {
    return lowerValue;
  }

  const baseLocale = lowerValue.split("-")[0];
  return supportedLocales.includes(baseLocale) ? baseLocale : null;
}

function getLocaleFromQuery() {
  if (typeof window === "undefined") {
    return null;
  }

  const params = new URLSearchParams(window.location.search);
  return normalizeLocale(params.get("lang"));
}

function syncLocaleQuery(localeCode) {
  if (typeof window === "undefined") {
    return;
  }

  const url = new URL(window.location.href);
  if (localeCode === "en") {
    url.searchParams.delete("lang");
  } else {
    url.searchParams.set("lang", localeCode);
  }
  window.history.replaceState({}, "", url.toString());
}

// Initialize with English as default, detect browser locale
export async function setupI18n() {
  const initialLocale =
    getLocaleFromQuery() ||
    normalizeLocale(getStoredLocale()) ||
    normalizeLocale(getLocaleFromNavigator()) ||
    "en";

  init({
    fallbackLocale: "en",
    initialLocale,
  });

  syncLocaleQuery(initialLocale);

  // Wait for the locale to be loaded before continuing
  await waitLocale();
}

// Get stored locale from localStorage
function getStoredLocale() {
  if (typeof localStorage !== "undefined") {
    return normalizeLocale(localStorage.getItem("locale"));
  }
  return null;
}

// Set and persist locale
export function setLocale(newLocale) {
  const normalizedLocale = normalizeLocale(newLocale) || "en";
  locale.set(normalizedLocale);
  if (typeof localStorage !== "undefined") {
    localStorage.setItem("locale", normalizedLocale);
  }
  syncLocaleQuery(normalizedLocale);
}

// Available locales with their display names and flags
export const availableLocales = [
  { code: "en", name: "English", flag: "🇬🇧" },
  { code: "es", name: "Español", flag: "🇪🇸" },
  { code: "pt", name: "Português", flag: "🇧🇷" },
  { code: "fr", name: "Français", flag: "🇫🇷" },
];

// Re-export for convenience
export { locale } from "svelte-i18n";
