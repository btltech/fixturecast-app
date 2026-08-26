import LEAGUES_DATA from "../../../data/leagues.json";
import { getLeagueLandingContent } from "../../src/services/leagueLandingContent.js";

const BACKEND_API_URL = "https://backend-api-production-7b7d.up.railway.app";
const APP_URL = "https://fixturecast.com";

const CRAWLER_USER_AGENTS = [
  "Googlebot",
  "Bingbot",
  "baiduspider",
  "YandexBot",
  "DuckDuckBot",
  "Applebot",
  "facebookexternalhit",
  "Facebot",
  "Twitterbot",
  "LinkedInBot",
  "WhatsApp",
  "TelegramBot",
  "Slackbot",
  "Discordbot",
  "Pinterest",
  "vkShare",
  "W3C_Validator",
];

const LEAGUE_BY_ID = new Map(LEAGUES_DATA.map((league) => [String(league.id), league]));

function isCrawler(userAgent) {
  if (!userAgent) return false;
  return CRAWLER_USER_AGENTS.some((crawler) =>
    userAgent.toLowerCase().includes(crawler.toLowerCase()),
  );
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    switch (char) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      case "'":
        return "&#39;";
      default:
        return char;
    }
  });
}

function renderSchema(schema) {
  const items = Array.isArray(schema) ? schema : [schema];
  return items
    .map(
      (item) =>
        `\n  <script type="application/ld+json">${JSON.stringify(item)}</script>`,
    )
    .join("");
}

function buildHtml({ title, description, url, image, keywords, schema, body }) {
  const safeTitle = escapeHtml(title);
  const safeDescription = escapeHtml(description);
  const safeUrl = escapeHtml(url);
  const safeImage = escapeHtml(image);
  const safeKeywords = escapeHtml(keywords);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${safeTitle}</title>
  <meta name="description" content="${safeDescription}">
  <meta name="keywords" content="${safeKeywords}">
  <meta name="robots" content="index,follow,max-image-preview:large">

  <link rel="canonical" href="${safeUrl}">

  <meta property="og:type" content="website">
  <meta property="og:url" content="${safeUrl}">
  <meta property="og:title" content="${safeTitle}">
  <meta property="og:description" content="${safeDescription}">
  <meta property="og:image" content="${safeImage}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="${safeTitle}">
  <meta property="og:site_name" content="FixtureCast">

  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:url" content="${safeUrl}">
  <meta name="twitter:title" content="${safeTitle}">
  <meta name="twitter:description" content="${safeDescription}">
  <meta name="twitter:image" content="${safeImage}">
  <meta name="twitter:site" content="@fixturecast">${renderSchema(schema)}
</head>
<body>
${body}
</body>
</html>`;
}

function getTierLabel(tier) {
  if (tier === 0) return "FIFA/Continental";
  if (tier === 1) return "Top Division";
  if (tier === 2) return "Second Division";
  if (tier === 3) return "Cup Competition";
  return "Football";
}

function formatDate(dateValue) {
  if (!dateValue) return "Date TBD";
  try {
    return new Date(dateValue).toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  } catch {
    return "Date TBD";
  }
}

function formatTime(dateValue) {
  if (!dateValue) return "TBD";
  try {
    return new Date(dateValue).toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return "TBD";
  }
}

async function fetchFixtures(leagueId) {
  try {
    const response = await fetch(
      `${BACKEND_API_URL}/api/fixtures?league=${encodeURIComponent(leagueId)}&next=8`,
      { signal: AbortSignal.timeout(5000) },
    );
    if (!response.ok) return [];

    const data = await response.json();
    return Array.isArray(data.response) ? data.response.slice(0, 8) : [];
  } catch {
    return [];
  }
}

function buildLeagueSeo(league) {
  const tierLabel = getTierLabel(league.tier);
  const country = league.country && league.country !== "World" ? league.country : "";

  return {
    title: `${league.emoji} ${league.name} Predictions, Fixtures & Standings | FixtureCast`,
    description: `AI-powered ${league.name} predictions, upcoming fixtures, live standings and results. ${country ? `${country} ${tierLabel}` : tierLabel} — all matches covered by FixtureCast's ML engine. Updated daily.`,
    image: `${BACKEND_API_URL}/api/og-image/home`,
    url: `${APP_URL}/league/${league.id}`,
    keywords: `${league.name} predictions, ${league.name} fixtures, ${league.name} standings, ${country ? `${country} football` : "football"} predictions, AI football predictions`,
    schema: [
      {
        "@context": "https://schema.org",
        "@type": "SportsOrganization",
        name: league.name,
        sport: "Soccer",
        ...(country
          ? { location: { "@type": "Place", name: country } }
          : {}),
      },
      {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: APP_URL },
          {
            "@type": "ListItem",
            position: 2,
            name: "Predictions",
            item: `${APP_URL}/predictions`,
          },
          {
            "@type": "ListItem",
            position: 3,
            name: league.name,
            item: `${APP_URL}/league/${league.id}`,
          },
        ],
      },
    ],
  };
}

function buildFixturesMarkup(fixtures, leagueId) {
  if (!fixtures.length) {
    return "<p>Upcoming fixtures will appear here as new matches are published.</p>";
  }

  const items = fixtures
    .map((fixture) => {
      const fixtureId = fixture.fixture?.id;
      const homeName = fixture.teams?.home?.name || "Home Team";
      const awayName = fixture.teams?.away?.name || "Away Team";
      const date = fixture.fixture?.date;
      const href = `${APP_URL}/prediction/${fixtureId}?league=${leagueId}`;

      return `<li><a href="${escapeHtml(href)}">${escapeHtml(homeName)} vs ${escapeHtml(awayName)}</a> <span>${escapeHtml(formatDate(date))} at ${escapeHtml(formatTime(date))}</span></li>`;
    })
    .join("\n");

  return `<ul>${items}</ul>`;
}

function buildBody(league, seo, fixtures) {
  const tierLabel = getTierLabel(league.tier);
  const country = league.country && league.country !== "World" ? league.country : "Global";
  const landingContent = getLeagueLandingContent(league);
  const introMarkup = landingContent.intro
    .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
    .join("\n    ");
  const highlightsMarkup = landingContent.highlights.length
    ? `<ul>${landingContent.highlights
        .map((item) => `<li>${escapeHtml(item)}</li>`)
        .join("")}</ul>`
    : "";

  return `<main>
  <header>
    <h1>${escapeHtml(`${league.emoji} ${league.name} Predictions, Fixtures & Standings`)}</h1>
    <p>${escapeHtml(seo.description)}</p>
    <p>${escapeHtml(`${country} ${tierLabel}. Browse league fixtures, standings and AI-backed match predictions on FixtureCast.`)}</p>
  </header>

  <section>
    <h2>${escapeHtml(landingContent.coverageHeading)}</h2>
    ${introMarkup}
    ${highlightsMarkup}
  </section>

  <section>
    <h2>Upcoming ${escapeHtml(league.name)} fixtures</h2>
    ${buildFixturesMarkup(fixtures, league.id)}
  </section>

  <nav>
    <p><a href="${escapeHtml(`${APP_URL}/predictions?league=${league.id}`)}">View all ${escapeHtml(league.name)} predictions</a></p>
    <p><a href="${escapeHtml(`${APP_URL}/fixtures?league=${league.id}`)}">See more ${escapeHtml(league.name)} fixtures</a></p>
  </nav>
</main>`;
}

export async function onRequest(context) {
  const { request, params, next } = context;
  const userAgent = request.headers.get("user-agent") || "";

  if (!isCrawler(userAgent)) {
    return next();
  }

  const league = LEAGUE_BY_ID.get(String(params.id));
  if (!league) {
    return next();
  }

  try {
    const fixtures = await fetchFixtures(league.id);
    const seo = buildLeagueSeo(league);
    const html = buildHtml({
      ...seo,
      body: buildBody(league, seo, fixtures),
    });

    return new Response(html, {
      headers: {
        "content-type": "text/html;charset=UTF-8",
        "cache-control": "public, max-age=3600",
      },
    });
  } catch (error) {
    console.error("Error generating league crawler page:", error);
    return next();
  }
}