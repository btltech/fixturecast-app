import { normalizeLocale } from "./index.js";

const dateLocales = {
  en: "en-GB",
  es: "es-ES",
  pt: "pt-BR",
  fr: "fr-FR",
};

export function getDateLocale(localeCode) {
  return dateLocales[normalizeLocale(localeCode) || "en"] || dateLocales.en;
}

export function formatDate(value, localeCode, options = {}) {
  if (!value) {
    return "";
  }

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat(getDateLocale(localeCode), options).format(date);
}

export function formatNumber(value, localeCode, options = {}) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "";
  }

  return new Intl.NumberFormat(getDateLocale(localeCode), options).format(value);
}