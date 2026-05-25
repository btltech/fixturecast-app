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

// Embedded league lookup — sourced from data/leagues.json at build time.
// Avoids network calls during SSR so league pages never fail.
const LEAGUE_MAP = {
    1:   { name: "FIFA World Cup",               country: "World" },
    2:   { name: "Champions League",             country: "Europe" },
    3:   { name: "Europa League",                country: "Europe" },
    5:   { name: "UEFA Nations League",          country: "Europe" },
    6:   { name: "AFCON",                        country: "Africa" },
    8:   { name: "International Friendlies",     country: "World" },
    9:   { name: "Club Friendlies",              country: "World" },
    11:  { name: "Copa Sudamericana",            country: "South America" },
    12:  { name: "CAF Champions League",         country: "Africa" },
    13:  { name: "Copa Libertadores",            country: "South America" },
    15:  { name: "FIFA Club World Cup",          country: "World" },
    16:  { name: "CONCACAF Champions Cup",       country: "North America" },
    17:  { name: "AFC Champions League Elite",   country: "Asia" },
    22:  { name: "CONCACAF Gold Cup",            country: "North America" },
    29:  { name: "WCQ - South America",          country: "World" },
    30:  { name: "WCQ - Asia",                   country: "World" },
    31:  { name: "WCQ - CONCACAF",               country: "World" },
    32:  { name: "WCQ - Europe",                 country: "World" },
    34:  { name: "WCQ - Africa",                 country: "World" },
    39:  { name: "Premier League",               country: "England" },
    40:  { name: "Championship",                 country: "England" },
    41:  { name: "League One",                   country: "England" },
    42:  { name: "League Two",                   country: "England" },
    43:  { name: "National League",              country: "England" },
    45:  { name: "FA Cup",                       country: "England" },
    46:  { name: "EFL Trophy",                   country: "England" },
    48:  { name: "League Cup",                   country: "England" },
    61:  { name: "Ligue 1",                      country: "France" },
    62:  { name: "Ligue 2",                      country: "France" },
    66:  { name: "Coupe de France",              country: "France" },
    71:  { name: "Brasileirão",                  country: "Brazil" },
    73:  { name: "Copa do Brasil",               country: "Brazil" },
    78:  { name: "Bundesliga",                   country: "Germany" },
    79:  { name: "2. Bundesliga",                country: "Germany" },
    81:  { name: "DFB-Pokal",                    country: "Germany" },
    88:  { name: "Eredivisie",                   country: "Netherlands" },
    94:  { name: "Primeira Liga",                country: "Portugal" },
    98:  { name: "J1 League",                    country: "Japan" },
    103: { name: "Eliteserien",                  country: "Norway" },
    106: { name: "Polish Ekstraklasa",           country: "Poland" },
    113: { name: "Allsvenskan",                  country: "Sweden" },
    116: { name: "Faroese Premier League",       country: "Faroe Islands" },
    119: { name: "Danish Superliga",             country: "Denmark" },
    128: { name: "Argentine Primera División",   country: "Argentina" },
    130: { name: "Copa Argentina",               country: "Argentina" },
    135: { name: "Serie A",                      country: "Italy" },
    136: { name: "Serie B",                      country: "Italy" },
    137: { name: "Coppa Italia",                 country: "Italy" },
    140: { name: "La Liga",                      country: "Spain" },
    141: { name: "Segunda División",             country: "Spain" },
    143: { name: "Copa del Rey",                 country: "Spain" },
    144: { name: "Belgian Pro League",           country: "Belgium" },
    164: { name: "Icelandic Úrvalsdeild",        country: "Iceland" },
    169: { name: "Chinese Super League",         country: "China" },
    179: { name: "Scottish Premiership",         country: "Scotland" },
    181: { name: "Scottish FA Cup",              country: "Scotland" },
    183: { name: "Maltese Premier League",       country: "Malta" },
    188: { name: "A-League",                     country: "Australia" },
    197: { name: "Greek Super League",           country: "Greece" },
    198: { name: "Algerian Ligue Pro 1",         country: "Algeria" },
    200: { name: "Moroccan Botola Pro",          country: "Morocco" },
    203: { name: "Süper Lig",                    country: "Turkey" },
    207: { name: "Swiss Super League",           country: "Switzerland" },
    210: { name: "Croatian HNL",                 country: "Croatia" },
    213: { name: "Tunisian Ligue 1",             country: "Tunisia" },
    218: { name: "Austrian Bundesliga",          country: "Austria" },
    233: { name: "Egyptian Premier League",      country: "Egypt" },
    235: { name: "Russian Premier League",       country: "Russia" },
    239: { name: "Colombian Primera A",          country: "Colombia" },
    244: { name: "Finnish Veikkausliiga",        country: "Finland" },
    253: { name: "MLS",                          country: "USA" },
    255: { name: "USL Championship",             country: "USA" },
    262: { name: "Liga MX",                      country: "Mexico" },
    265: { name: "Chilean Primera",              country: "Chile" },
    271: { name: "Israeli Premier League",       country: "Israel" },
    278: { name: "Malaysian Super League",       country: "Malaysia" },
    283: { name: "Romanian Liga 1",              country: "Romania" },
    286: { name: "Serbian SuperLiga",            country: "Serbia" },
    289: { name: "South African PSL",            country: "South Africa" },
    292: { name: "K League 1",                   country: "South Korea" },
    296: { name: "Thai League 1",                country: "Thailand" },
    307: { name: "Saudi Pro League",             country: "Saudi Arabia" },
    323: { name: "Indian Super League",          country: "India" },
    332: { name: "Nigerian Pro League",          country: "Nigeria" },
    333: { name: "Ukrainian Premier League",     country: "Ukraine" },
    338: { name: "Ghanaian Premier League",      country: "Ghana" },
    340: { name: "Vietnam V-League 1",           country: "Vietnam" },
    345: { name: "Czech First League",           country: "Czech Republic" },
    435: { name: "UAE Pro League",               country: "UAE" },
    848: { name: "Conference League",            country: "Europe" },
};

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
            description: "Free AI predictions for football matches across global competitions. Premier League, Champions League, La Liga, Serie A, Bundesliga, FIFA World Cup Qualifiers, Copa Libertadores, MLS and more. Win probabilities, predicted scores, updated daily.",
            schema: [
                {
                    "@context": "https://schema.org",
                    "@type": "WebSite",
                    name: "FixtureCast",
                    description: "AI-powered football match predictions across global competitions",
                    url: APP_URL,
                },
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    name: "FixtureCast",
                    url: APP_URL,
                    logo: `${APP_URL}/icons/icon-192.png`,
                    description: "AI-powered football match predictions across global competitions worldwide",
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
            description: `AI-powered predictions for all football matches today (${today}). Win probabilities, predicted scores, and detailed analysis across major competitions including Premier League, La Liga, Serie A, Champions League and Copa Libertadores.`,
        },
        "/ai": {
            title: "AI Match Predictions | FixtureCast",
            description: "AI-powered football predictions with win probabilities and predicted scores. Covering major football competitions including Premier League, La Liga, Serie A, Bundesliga, UEFA Champions League, MLS and Copa Libertadores.",
        },
        "/predictions": {
            title: "AI Match Predictions | FixtureCast",
            description: "AI-powered football predictions with win probabilities and predicted scores. Covering major football competitions including Premier League, La Liga, Serie A, Bundesliga, UEFA Champions League, MLS and Copa Libertadores.",
        },
        "/smart-markets": {
            title: "Smart Markets — AI Value Bets | FixtureCast",
            description: "AI-identified value bets where we beat the market. Over/Under 2.5 goals and BTTS predictions with 60%+ confidence. Only real-edge picks across global football competitions.",
        },
        "/accumulators": {
            title: "Daily Accumulator Tips | FixtureCast",
            description: "AI-generated daily accumulator bets across major football competitions. 8-fold, 6-fold, 4-fold and BTTS accas built from high-confidence predictions — Premier League, La Liga, Copa Libertadores and more.",
        },
        "/live": {
            title: "Live Scores | FixtureCast",
            description: "Follow live football scores and match updates across global competitions worldwide. Real-time results for Premier League, La Liga, Serie A, Champions League, MLS and more.",
        },
        "/standings": {
            title: "League Standings & Tables | FixtureCast",
            description: "Live league tables for global football competitions. Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, Europa League, Copa Libertadores and more — standings updated daily.",
        },
        "/teams": {
            title: "Football Team Statistics | FixtureCast",
            description: "Detailed team statistics, form guides, and home or away records across global football competitions. Analyse teams from Premier League, La Liga, Serie A, Bundesliga, MLS and more.",
        },
        "/results": {
            title: "Football Results | FixtureCast",
            description: "Latest football match results and final scores from global competitions. Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, Europa League and Copa Libertadores results updated daily.",
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

/**
 * Generate SEO metadata for a league page using the embedded LEAGUE_MAP.
 * Pure function — no network calls, cannot fail.
 */
function getLeagueSEO(leagueId) {
    const league = LEAGUE_MAP[leagueId];
    const leagueName = league ? league.name : `League #${leagueId}`;
    const country = league ? league.country : "";
    const locationStr = country && country !== "World" ? ` — ${country}` : "";

    return {
        title: `${leagueName} Predictions, Fixtures & Results${locationStr} | FixtureCast`,
        description: `AI-powered match predictions for ${leagueName}${locationStr}. Win probabilities, predicted scores, and form analysis for every fixture.`,
        schema: {
            "@context": "https://schema.org",
            "@type": "SportsOrganization",
            name: leagueName,
            url: `${APP_URL}/league/${leagueId}`,
        },
    };
}

/**
 * Generate SEO metadata for a team page.
 * Attempts a 2-second API fetch for the real team name; falls back to
 * "Team #id" so crawlers always receive a proper HTML response.
 */
async function getTeamSEO(teamId, leagueId) {
    const league = leagueId ? LEAGUE_MAP[leagueId] : null;
    const leagueName = league ? league.name : null;

    let teamName = null;
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);
        const resp = await fetch(
            `https://api.fixturecast.com/api/teams?id=${teamId}`,
            { signal: controller.signal },
        );
        clearTimeout(timeoutId);
        if (resp.ok) {
            const data = await resp.json();
            const teams = data?.response;
            if (Array.isArray(teams) && teams.length > 0) {
                teamName = teams[0]?.team?.name || null;
            }
        }
    } catch {
        // Timeout or network error — safe fallback below
    }

    const displayName = teamName || `Team #${teamId}`;
    const leagueStr = leagueName ? ` — ${leagueName}` : "";

    return {
        title: `${displayName} Predictions & Fixtures${leagueStr} | FixtureCast`,
        description: `AI-powered predictions and fixtures for ${displayName}${leagueStr}. Win probabilities, form analysis, and predicted scores.`,
        schema: {
            "@context": "https://schema.org",
            "@type": "SportsTeam",
            name: displayName,
            url: `${APP_URL}/team/${teamId}${leagueId ? `?league=${leagueId}` : ""}`,
        },
    };
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
    if (seo) {
        return new Response(buildSSRPage(seo, pathname), {
            headers: {
                "content-type": "text/html;charset=UTF-8",
                "cache-control": "public, max-age=3600",
            },
        });
    }

    // Dynamic: /league/:id — pure lookup, no network call
    const leagueMatch = pathname.match(/^\/league\/(\d+)$/);
    if (leagueMatch) {
        const leagueSeo = getLeagueSEO(parseInt(leagueMatch[1]));
        return new Response(buildSSRPage(leagueSeo, pathname), {
            headers: {
                "content-type": "text/html;charset=UTF-8",
                "cache-control": "public, max-age=7200",
            },
        });
    }

    // Dynamic: /team/:id (with optional ?league= query param)
    const teamMatch = pathname.match(/^\/team\/(\d+)$/);
    if (teamMatch) {
        const teamId = parseInt(teamMatch[1]);
        const leagueId = url.searchParams.get("league")
            ? parseInt(url.searchParams.get("league"))
            : null;
        const teamSeo = await getTeamSEO(teamId, leagueId);
        const teamPath = url.pathname + (leagueId ? `?league=${leagueId}` : "");
        return new Response(buildSSRPage(teamSeo, teamPath), {
            headers: {
                "content-type": "text/html;charset=UTF-8",
                "cache-control": "public, max-age=3600",
            },
        });
    }

    return next();
}
