<script>
  import { onMount } from "svelte";
  import { locale } from "../lib/i18n";

  export let data = {};

  const ogLocaleMap = {
    en: "en_US",
    es: "es_ES",
    pt: "pt_BR",
    fr: "fr_FR",
  };

  const supportedLocales = ["en", "es", "pt", "fr"];

  // SEO metadata
  $: title = data.title || "FixtureCast";
  $: description =
    data.description || "AI-powered football match predictions";
  $: origin = typeof window !== "undefined" ? window.location.origin : "https://fixturecast.com";
  $: image = data.image || `${origin}/default-og.png`;
  $: currentLocale = $locale || "en";
  $: url = getLocalizedUrl(data.url || (typeof window !== "undefined" ? window.location.href : origin), currentLocale);
  $: type = data.type || "website";
  $: schema = data.schema || null;
  $: alternates = data.alternates || buildAlternateUrls(data.url || (typeof window !== "undefined" ? window.location.href : origin));

  onMount(() => {
    if (typeof window !== "undefined") {
      updateMetaTags();
    }
  });

  function updateMetaTags() {
    // Update title
    document.title = title;

    // Update or create meta tags
    updateOrCreateMeta("description", description);

    // Open Graph
    updateOrCreateMeta("og:title", title, "property");
    updateOrCreateMeta("og:description", description, "property");
    updateOrCreateMeta("og:image", image, "property");
    updateOrCreateMeta("og:url", url, "property");
    updateOrCreateMeta("og:type", type, "property");
    updateOrCreateMeta("og:site_name", "FixtureCast", "property");
    updateOrCreateMeta("og:locale", ogLocaleMap[currentLocale] || ogLocaleMap.en, "property");
    updateOgLocaleAlternates();

    // Twitter Card
    updateOrCreateMeta("twitter:card", "summary_large_image");
    updateOrCreateMeta("twitter:title", title);
    updateOrCreateMeta("twitter:description", description);
    updateOrCreateMeta("twitter:image", image);

    // Canonical URL
    updateOrCreateLink("canonical", url);
    updateAlternateLinks();

    document.documentElement.lang = currentLocale;

    // Schema.org structured data
    if (schema) {
      updateOrCreateSchema(schema);
    }
  }

  function updateOrCreateMeta(name, content, attribute = "name") {
    let meta = document.querySelector(`meta[${attribute}="${name}"]`);
    if (!meta) {
      meta = document.createElement("meta");
      meta.setAttribute(attribute, name);
      document.head.appendChild(meta);
    }
    meta.setAttribute("content", content);
  }

  function updateOrCreateLink(rel, href) {
    let link = document.querySelector(`link[rel="${rel}"]`);
    if (!link) {
      link = document.createElement("link");
      link.setAttribute("rel", rel);
      document.head.appendChild(link);
    }
    link.setAttribute("href", href);
  }

  function updateAlternateLinks() {
    document.querySelectorAll('link[rel="alternate"][data-seohead-alt="true"]').forEach((el) => el.remove());

    Object.entries(alternates).forEach(([lang, href]) => {
      const link = document.createElement("link");
      link.setAttribute("rel", "alternate");
      link.setAttribute("hreflang", lang);
      link.setAttribute("href", href);
      link.setAttribute("data-seohead-alt", "true");
      document.head.appendChild(link);
    });

    const defaultLink = document.createElement("link");
    defaultLink.setAttribute("rel", "alternate");
    defaultLink.setAttribute("hreflang", "x-default");
    defaultLink.setAttribute("href", alternates.en || url);
    defaultLink.setAttribute("data-seohead-alt", "true");
    document.head.appendChild(defaultLink);
  }

  function updateOgLocaleAlternates() {
    document.querySelectorAll('meta[property="og:locale:alternate"][data-seohead-alt="true"]').forEach((el) => el.remove());

    supportedLocales
      .filter((lang) => lang !== currentLocale)
      .forEach((lang) => {
        const meta = document.createElement("meta");
        meta.setAttribute("property", "og:locale:alternate");
        meta.setAttribute("content", ogLocaleMap[lang] || ogLocaleMap.en);
        meta.setAttribute("data-seohead-alt", "true");
        document.head.appendChild(meta);
      });
  }

  function getLocalizedUrl(rawUrl, localeCode) {
    const localizedUrl = new URL(rawUrl, origin);
    if (localeCode === "en") {
      localizedUrl.searchParams.delete("lang");
    } else {
      localizedUrl.searchParams.set("lang", localeCode);
    }
    return localizedUrl.toString();
  }

  function buildAlternateUrls(rawUrl) {
    return supportedLocales.reduce((entries, lang) => {
      entries[lang] = getLocalizedUrl(rawUrl, lang);
      return entries;
    }, {});
  }

  function updateOrCreateSchema(schemaData) {
    // Remove all existing ld+json scripts managed by SEOHead
    document.querySelectorAll('script[type="application/ld+json"].seohead-schema')
      .forEach((el) => el.remove());

    const schemas = Array.isArray(schemaData) ? schemaData : [schemaData];
    schemas.forEach((s) => {
      const script = document.createElement("script");
      script.setAttribute("type", "application/ld+json");
      script.setAttribute("class", "seohead-schema");
      script.textContent = JSON.stringify(s);
      document.head.appendChild(script);
    });
  }

  // Watch for data changes and update meta tags
  $: if (title) updateMetaTags();
</script>
