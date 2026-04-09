/**
 * Dynamic Sitemap Generator — Cloudflare Pages Function
 *
 * Serves /sitemap.xml by querying the backend for upcoming fixtures
 * across all featured leagues, then generating a valid sitemap XML
 * that includes both static pages and dynamic prediction URLs.
 *
 * Also pings Google and Bing when the sitemap is regenerated.
 */

const BACKEND_API_URL = "https://backend-api-production-7b7d.up.railway.app";
const APP_URL = "https://fixturecast.com";
const SITEMAP_URL = `${APP_URL}/sitemap.xml`;

// Leagues with landing pages in the sitemap (canonical tier 0-2 competitions).
const LEAGUE_PAGE_IDS = [
    1, 29, 30, 31, 32, 34, 15, 17, 16, 22, 6, 2, 3, 848, 5, 13, 11, 12,
    39, 140, 135, 78, 61, 88, 94, 218, 207, 119, 113, 103, 307, 71, 203,
    253, 179, 144, 128, 262, 98, 239, 265, 292, 323, 435, 233, 289, 200,
    213, 198, 332, 338, 197, 106, 271, 283, 345, 235, 333, 210, 286, 188,
    116, 183, 244, 164, 169, 296, 278, 340, 255, 40, 141, 136, 79, 62,
    41, 42, 43,
];

// Featured leagues to include in fixture URLs within the sitemap.
const FEATURED_LEAGUE_IDS = [
    // European competitions
    2,    // UEFA Champions League
    3,    // UEFA Europa League
    848,  // UEFA Conference League
    // Top European & domestic leagues
    39,   // Premier League
    140,  // La Liga
    135,  // Serie A
    78,   // Bundesliga
    61,   // Ligue 1
    88,   // Eredivisie
    94,   // Primeira Liga
    218,  // Austrian Bundesliga
    207,  // Swiss Super League
    119,  // Danish Superliga
    113,  // Allsvenskan
    103,  // Eliteserien
    // International top leagues
    307,  // Saudi Pro League
    71,   // Brasileirão
    203,  // Süper Lig
    253,  // MLS
    179,  // Scottish Premiership
    144,  // Belgian Pro League
    // Americas & Asia
    128,  // Argentine Primera División
    262,  // Liga MX
    98,   // J1 League
    239,  // Colombian Primera A
    265,  // Chilean Primera
    292,  // K League 1
    323,  // Indian Super League
    435,  // UAE Pro League
    // Africa
    233,  // Nigerian Premier League
    289,  // South African PSL
    200,  // Egyptian Premier League
    213,  // Moroccan Botola
    198,  // Tunisian Ligue 1
    332,  // Ghanaian Premier League
    338,  // Kenyan Premier League
    // Europe expansion
    197,  // Faroese Premier League
    106,  // Finnish Veikkausliiga
    271,  // Icelandic Úrvalsdeild
    283,  // Maltese Premier League
    345,  // Chinese Super League
    // High-scoring small leagues
    116,  // Latvian Higher League
    183,  // Estonian Meistriliiga
    244,  // Kazakhstani Premier League
    164,  // Armenian Premier League
    169,  // Georgian Erovnuli Liga
    // Second divisions
    40,   // Championship (England)
    141,  // Segunda División (Spain)
    136,  // Serie B (Italy)
    79,   // 2. Bundesliga (Germany)
    62,   // Ligue 2 (France)
    // Domestic cups
    45,   // FA Cup
    48,   // League Cup
];

// Static pages with their change frequency and priority
const STATIC_PAGES = [
    { path: "/", changefreq: "daily", priority: "1.0" },
    { path: "/today", changefreq: "daily", priority: "0.9" },
    { path: "/fixtures", changefreq: "daily", priority: "0.9" },
    { path: "/ai", changefreq: "daily", priority: "0.8" },
    { path: "/predictions", changefreq: "daily", priority: "0.8" },
    { path: "/live", changefreq: "always", priority: "0.8" },
    { path: "/smart-markets", changefreq: "daily", priority: "0.7" },
    { path: "/accumulators", changefreq: "daily", priority: "0.7" },
    { path: "/standings", changefreq: "weekly", priority: "0.7" },
    { path: "/teams", changefreq: "weekly", priority: "0.7" },
    { path: "/picks", changefreq: "daily", priority: "0.7" },
    { path: "/results", changefreq: "daily", priority: "0.6" },
    { path: "/models", changefreq: "weekly", priority: "0.6" },
    { path: "/history", changefreq: "daily", priority: "0.4" },
    { path: "/privacy", changefreq: "monthly", priority: "0.3" },
    { path: "/terms", changefreq: "monthly", priority: "0.3" },
    { path: "/cookies", changefreq: "monthly", priority: "0.3" },
];

/**
 * Fetch fixture IDs for a league from the backend.
 * Returns an array of { id, leagueId, date } objects.
 */
async function fetchFixturesForLeague(leagueId) {
    try {
        const res = await fetch(
            `${BACKEND_API_URL}/api/fixtures?league=${leagueId}&next=30`,
            { signal: AbortSignal.timeout(5000) }
        );
        if (!res.ok) return [];

        const data = await res.json();
        if (!data.response || !Array.isArray(data.response)) return [];

        return data.response.map((f) => ({
            id: f.fixture.id,
            leagueId: f.league.id,
            date: f.fixture.date,
        }));
    } catch {
        return [];
    }
}

/**
 * Build the sitemap XML string.
 */
function buildSitemapXML(fixtures) {
    const today = new Date().toISOString().split("T")[0];

    let xml = `<?xml version="1.0" encoding="UTF-8"?>\n`;
    xml += `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n`;

    // Static pages
    for (const page of STATIC_PAGES) {
        xml += `  <url>\n`;
        xml += `    <loc>${APP_URL}${page.path}</loc>\n`;
        xml += `    <lastmod>${today}</lastmod>\n`;
        xml += `    <changefreq>${page.changefreq}</changefreq>\n`;
        xml += `    <priority>${page.priority}</priority>\n`;
        xml += `  </url>\n`;
    }

    for (const leagueId of LEAGUE_PAGE_IDS) {
        xml += `  <url>\n`;
        xml += `    <loc>${APP_URL}/league/${leagueId}</loc>\n`;
        xml += `    <lastmod>${today}</lastmod>\n`;
        xml += `    <changefreq>daily</changefreq>\n`;
        xml += `    <priority>0.7</priority>\n`;
        xml += `  </url>\n`;
    }

    // De-duplicate fixtures by ID (in case the same fixture shows up in
    // multiple league queries, e.g. European competitions)
    const seen = new Set();
    for (const fixture of fixtures) {
        if (seen.has(fixture.id)) continue;
        seen.add(fixture.id);

        const lastmod = fixture.date
            ? new Date(fixture.date).toISOString().split("T")[0]
            : today;

        xml += `  <url>\n`;
        xml += `    <loc>${APP_URL}/prediction/${fixture.id}?league=${fixture.leagueId}</loc>\n`;
        xml += `    <lastmod>${lastmod}</lastmod>\n`;
        xml += `    <changefreq>daily</changefreq>\n`;
        xml += `    <priority>0.8</priority>\n`;
        xml += `  </url>\n`;
    }

    xml += `</urlset>\n`;
    return xml;
}

/**
 * Ping search engines to notify them the sitemap has been updated.
 * Google has deprecated the ping endpoint but it still works as a best-effort signal.
 * For Google, submitting via Search Console or robots.txt directive is preferred (already done).
 */
async function pingSearchEngines() {
    const pings = [
        `https://www.google.com/ping?sitemap=${encodeURIComponent(SITEMAP_URL)}`,
        `https://www.bing.com/ping?sitemap=${encodeURIComponent(SITEMAP_URL)}`,
    ];

    // Fire-and-forget — don't block the response on ping results
    await Promise.allSettled(
        pings.map((url) =>
            fetch(url, { signal: AbortSignal.timeout(3000) }).catch(() => { })
        )
    );
}

/**
 * Submit URLs to IndexNow (Bing, Yandex, and other supporting engines).
 * This pushes individual prediction URLs for faster indexing of time-sensitive content.
 * https://www.indexnow.org/documentation
 */
const INDEXNOW_KEY = "c981f578e26871b13da98e23fdc87ef2";

async function submitIndexNow(fixtures) {
    if (!fixtures.length) return;

    // Deduplicate and build URL list (limit to 10,000 per IndexNow spec)
    const seen = new Set();
    const urlList = [];
    for (const f of fixtures) {
        if (seen.has(f.id)) continue;
        seen.add(f.id);
        urlList.push(`${APP_URL}/prediction/${f.id}?league=${f.leagueId}`);
        if (urlList.length >= 10000) break;
    }

    const payload = {
        host: "fixturecast.com",
        key: INDEXNOW_KEY,
        keyLocation: `${APP_URL}/${INDEXNOW_KEY}.txt`,
        urlList,
    };

    try {
        await fetch("https://api.indexnow.org/IndexNow", {
            method: "POST",
            headers: { "Content-Type": "application/json; charset=utf-8" },
            body: JSON.stringify(payload),
            signal: AbortSignal.timeout(5000),
        });
    } catch {
        // Silent fail — IndexNow is best-effort
    }
}

export async function onRequest(context) {
    try {
        // Fetch fixtures from all featured leagues in parallel
        const fixtureArrays = await Promise.all(
            FEATURED_LEAGUE_IDS.map((leagueId) => fetchFixturesForLeague(leagueId))
        );

        // Flatten all fixtures into a single array
        const allFixtures = fixtureArrays.flat();

        // Build sitemap XML
        const sitemapXML = buildSitemapXML(allFixtures);

        // Ping search engines and submit to IndexNow asynchronously
        context.waitUntil(
            Promise.allSettled([
                pingSearchEngines(),
                submitIndexNow(allFixtures),
            ])
        );

        return new Response(sitemapXML, {
            headers: {
                "content-type": "application/xml; charset=UTF-8",
                "cache-control": "public, max-age=3600, s-maxage=3600",
            },
        });
    } catch (error) {
        console.error("Sitemap generation error:", error);

        // Fallback: serve static pages only
        const fallbackXML = buildSitemapXML([]);
        return new Response(fallbackXML, {
            headers: {
                "content-type": "application/xml; charset=UTF-8",
                "cache-control": "public, max-age=300",
            },
        });
    }
}
