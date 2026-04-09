/**
 * Cloudflare Pages Function to inject OG meta tags and structured data
 * for social media crawlers AND search engine bots.
 * Intercepts /prediction/:id routes and adds dynamic meta tags + JSON-LD.
 */

// Use the direct Railway URL since api.fixturecast.com custom domain
// may not resolve from Cloudflare Pages functions
const BACKEND_API_URL = "https://backend-api-production-7b7d.up.railway.app";
const APP_URL = "https://fixturecast.com";

// User agents for social media crawlers AND search engine bots
const CRAWLER_USER_AGENTS = [
  // Search engines
  "Googlebot",
  "Bingbot",
  "baiduspider",
  "YandexBot",
  "DuckDuckBot",
  "Applebot",
  // Social media crawlers
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

function isCrawler(userAgent) {
  if (!userAgent) return false;
  return CRAWLER_USER_AGENTS.some((crawler) =>
    userAgent.toLowerCase().includes(crawler.toLowerCase()),
  );
}

export async function onRequest(context) {
  const { request, params, next } = context;
  const userAgent = request.headers.get("user-agent") || "";

  // If not a crawler, serve the normal SPA
  if (!isCrawler(userAgent)) {
    return next();
  }

  // Extract fixture ID and league from URL
  const fixtureId = params.id;
  const url = new URL(request.url);
  const leagueId = url.searchParams.get("league") || "39";

  try {
    // Fetch fixture details from backend
    const fixtureRes = await fetch(
      `${BACKEND_API_URL}/api/fixtures?league=${leagueId}&next=50`,
    );
    let homeTeam = "Home Team";
    let awayTeam = "Away Team";
    let leagueName = "Football League";
    let matchDate = "";
    let matchDateISO = "";
    let venueName = "Stadium";
    let homeLogo = "";
    let awayLogo = "";

    if (fixtureRes.ok) {
      const data = await fixtureRes.json();
      const fixture = data.response?.find(
        (f) => f.fixture.id === parseInt(fixtureId),
      );
      if (fixture) {
        homeTeam = fixture.teams.home.name;
        awayTeam = fixture.teams.away.name;
        leagueName = fixture.league.name;
        homeLogo = fixture.teams.home.logo || "";
        awayLogo = fixture.teams.away.logo || "";
        venueName = fixture.fixture.venue?.name || "Stadium";
        matchDateISO = fixture.fixture.date;
        matchDate = new Date(fixture.fixture.date).toLocaleDateString("en-US", {
          month: "long",
          day: "numeric",
          year: "numeric",
        });
      }
    }

    // Build OG image URL
    const ogImage = `${BACKEND_API_URL}/api/og-image/${fixtureId}?league=${leagueId}`;
    const pageUrl = `${APP_URL}/prediction/${fixtureId}?league=${leagueId}`;

    // Generate title and description
    const title = `${homeTeam} vs ${awayTeam} Prediction${matchDate ? ` - ${matchDate}` : ""} | FixtureCast`;
    const description = `AI-powered prediction for ${homeTeam} vs ${awayTeam} in ${leagueName}. Get match odds, predicted score, BTTS, and Over 2.5 predictions.`;

    // Generate SportsEvent JSON-LD structured data
    const jsonLd = {
      "@context": "https://schema.org",
      "@type": "SportsEvent",
      name: `${homeTeam} vs ${awayTeam}`,
      description: `${leagueName} match between ${homeTeam} and ${awayTeam}`,
      startDate: matchDateISO || undefined,
      location: {
        "@type": "Place",
        name: venueName,
      },
      homeTeam: {
        "@type": "SportsTeam",
        name: homeTeam,
        logo: homeLogo || undefined,
      },
      awayTeam: {
        "@type": "SportsTeam",
        name: awayTeam,
        logo: awayLogo || undefined,
      },
      sport: "Soccer",
      competitionCategory: leagueName,
    };

    // Generate HTML with OG meta tags + JSON-LD for crawlers
    const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <meta name="description" content="${description}">
  <meta name="keywords" content="${homeTeam} vs ${awayTeam} prediction, ${leagueName} predictions, football predictions, AI predictions">

  <!-- Canonical URL -->
  <link rel="canonical" href="${pageUrl}">

  <!-- Open Graph / Facebook -->
  <meta property="og:type" content="website">
  <meta property="og:url" content="${pageUrl}">
  <meta property="og:title" content="${title}">
  <meta property="og:description" content="${description}">
  <meta property="og:image" content="${ogImage}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:site_name" content="FixtureCast">

  <!-- Twitter -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:url" content="${pageUrl}">
  <meta name="twitter:title" content="${title}">
  <meta name="twitter:description" content="${description}">
  <meta name="twitter:image" content="${ogImage}">
  <meta name="twitter:site" content="@fixturecast">

  <!-- JSON-LD Structured Data -->
  <script type="application/ld+json">${JSON.stringify(jsonLd)}</script>

  <!-- Redirect to actual page after a moment (for crawlers that execute JS) -->
  <meta http-equiv="refresh" content="0; url=${pageUrl}">
</head>
<body>
  <h1>${title}</h1>
  <p>${description}</p>
  <p>Redirecting to <a href="${pageUrl}">${pageUrl}</a>...</p>
</body>
</html>`;

    return new Response(html, {
      headers: {
        "content-type": "text/html;charset=UTF-8",
        "cache-control": "public, max-age=3600",
      },
    });
  } catch (error) {
    // On error, fall back to normal page
    console.error("Error generating OG page:", error);
    return next();
  }
}
