/**
 * Cloudflare Pages Middleware — SSR meta tags for ALL pages
 *
 * This middleware intercepts requests from search engine and social media
 * crawlers and returns server-rendered HTML with proper title, description,
 * OG tags, and JSON-LD for every public route — not just /prediction/:id.
 *
 * For non-crawler user agents, it passes through to the SPA.
 */

const APP_URL = "https://fixturecast.com";

// Crawler user agents (must match the list in functions/prediction/[id].js)
const CRAWLER_USER_AGENTS = [
    "Googlebot", "Bingbot", "baiduspider", "YandexBot", "DuckDuckBot", "Applebot",
    "facebookexternalhit", "Facebot", "Twitterbot", "LinkedInBot",
    "WhatsApp", "TelegramBot", "Slackbot", "Discordbot", "Pinterest", "vkShare",
    "W3C_Validator",
];

function isCrawler(userAgent) {
    if (!userAgent) return false;
    return CRAWLER_USER_AGENTS.some((c) =>
        userAgent.toLowerCase().includes(c.toLowerCase())
    );
}

/**
 * SEO metadata for each static route.
 * Mirrors the data from seoService.js but available server-side.
 */
function getPageSEO(pathname) {
    const today = new Date().toLocaleDateString("en-US", {
        month: "long", day: "numeric", year: "numeric",
    });

    const pages = {
        "/": {
            title: "FixtureCast — AI-Powered Football Match Predictions",
            description: "Free AI predictions for football matches across 51 leagues worldwide. Premier League, Champions League, La Liga, Serie A, Bundesliga & more. Win probabilities, predicted scores, updated daily.",
            schema: [
                {
                    "@context": "https://schema.org",
                    "@type": "WebSite",
                    name: "FixtureCast",
                    description: "AI-powered football match predictions across 51 leagues",
                    url: APP_URL,
                },
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    name: "FixtureCast",
                    url: APP_URL,
                    logo: `${APP_URL}/icons/icon-192.png`,
                    description: "AI-powered football match predictions across 51 leagues worldwide",
                    sameAs: [
                        "https://twitter.com/fixturecast",
                        "https://www.instagram.com/fixturecast",
                        "https://t.me/fixturecast",
                        "https://discord.gg/fixturecast",
                        "https://www.reddit.com/r/fixturecast",
                        "https://bsky.app/profile/fixturecast.bsky.social",
                    ],
                },
            ],
        },
        "/today": {
            title: `Today's Football Fixtures & Predictions — ${today} | FixtureCast`,
            description: `All football matches playing today (${today}) with AI win probabilities and predicted scores across Premier League, Champions League, La Liga, and more.`,
        },
        "/fixtures": {
            title: `Today's Football Predictions — ${today} | FixtureCast`,
            description: `AI-powered predictions for all football matches today (${today}). Win probabilities, predicted scores, and detailed analysis for 51 leagues including Premier League, La Liga, Serie A & Champions League.`,
        },
        "/ai": {
            title: "AI Match Predictions | FixtureCast",
            description: "AI-powered football predictions with win probabilities and predicted scores. Covering 51 leagues including Premier League, La Liga, Serie A, Bundesliga and UEFA Champions League.",
        },
        "/predictions": {
            title: "AI Match Predictions | FixtureCast",
            description: "AI-powered football predictions with win probabilities and predicted scores. Covering 51 leagues including Premier League, La Liga, Serie A, Bundesliga and UEFA Champions League.",
        },
        "/smart-markets": {
            title: "Smart Markets — AI Value Bets | FixtureCast",
            description: "AI-identified value bets where we beat the market. Over/Under 2.5 goals and BTTS predictions with 60%+ confidence. Only real-edge picks across 51 football leagues.",
        },
        "/accumulators": {
            title: "Daily Accumulator Tips | FixtureCast",
            description: "AI-generated daily accumulator bets across 51 football leagues. 8-fold, 6-fold, 4-fold and BTTS accas built from high-confidence predictions — Premier League, La Liga & more.",
        },
        "/live": {
            title: "Live Scores | FixtureCast",
            description: "Follow live football scores and match updates across 51 leagues worldwide. Real-time results for Premier League, La Liga, Serie A, Champions League & more.",
        },
        "/standings": {
            title: "League Standings & Tables | FixtureCast",
            description: "Live league tables for 51 football leagues. Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, Europa League & more — standings updated daily.",
        },
        "/teams": {
            title: "Football Team Statistics | FixtureCast",
            description: "Detailed team statistics, form guides, and home/away records across 51 football leagues. Analyse any team from Premier League, La Liga, Serie A, Bundesliga, and more.",
        },
        "/results": {
            title: "Football Results | FixtureCast",
            description: "Latest football match results and final scores from 51 leagues. Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League & Europa League results updated daily.",
        },
        "/models": {
            title: "AI Model Performance | FixtureCast",
            description: "Track the accuracy and performance of our 11 AI prediction models across different leagues and markets.",
        },
        "/history": {
            title: "Prediction History | FixtureCast",
            description: "Review your past prediction views and track AI accuracy over time.",
        },
        "/picks": {
            title: "Today's Top Picks | FixtureCast",
            description: "Curated AI picks for today's best football matches. High-confidence predictions backed by data.",
        },
        "/privacy": {
            title: "Privacy Policy | FixtureCast",
            description: "FixtureCast privacy policy — how we collect, use, and protect your data.",
        },
        "/terms": {
            title: "Terms of Service | FixtureCast",
            description: "FixtureCast terms of service and conditions of use.",
        },
        "/cookies": {
            title: "Cookie Policy | FixtureCast",
            description: "FixtureCast cookie policy — how we use cookies and similar technologies.",
        },
    };

    return pages[pathname] || null;
}

function buildSSRPage(seo, pathname) {
    const url = `${APP_URL}${pathname}`;
    const image = `${APP_URL}/default-og.png`;

    // Support single schema object or array of schemas
    let schemaScript = "";
    if (seo.schema) {
        const schemas = Array.isArray(seo.schema) ? seo.schema : [seo.schema];
        schemaScript = schemas
            .map((s) => `\n  <script type="application/ld+json">${JSON.stringify(s)}</script>`)
            .join("");
    }

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${seo.title}</title>
  <meta name="description" content="${seo.description}">

  <link rel="canonical" href="${url}">

  <meta property="og:type" content="website">
  <meta property="og:url" content="${url}">
  <meta property="og:title" content="${seo.title}">
  <meta property="og:description" content="${seo.description}">
  <meta property="og:image" content="${image}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:site_name" content="FixtureCast">

  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:url" content="${url}">
  <meta name="twitter:title" content="${seo.title}">
  <meta name="twitter:description" content="${seo.description}">
  <meta name="twitter:image" content="${image}">
  <meta name="twitter:site" content="@fixturecast">${schemaScript}
</head>
<body>
  <h1>${seo.title}</h1>
  <p>${seo.description}</p>
  <p><a href="${url}">Visit FixtureCast</a></p>
</body>
</html>`;
}

export async function onRequest(context) {
    const { request, next } = context;
    const userAgent = request.headers.get("user-agent") || "";

    // Only intercept for crawlers
    if (!isCrawler(userAgent)) {
        return next();
    }

    const url = new URL(request.url);
    const pathname = url.pathname.replace(/\/$/, "") || "/";

    // Skip paths handled by dedicated functions (prediction pages, sitemap)
    if (pathname.startsWith("/prediction/") || pathname === "/sitemap.xml") {
        return next();
    }

    // Skip asset paths
    if (pathname.startsWith("/assets/") || pathname.startsWith("/icons/")) {
        return next();
    }

    const seo = getPageSEO(pathname);
    if (!seo) {
        return next();
    }

    return new Response(buildSSRPage(seo, pathname), {
        headers: {
            "content-type": "text/html;charset=UTF-8",
            "cache-control": "public, max-age=3600",
        },
    });
}
