/**
 * Cloudflare Pages Function to inject OG meta tags and structured data
 * for social media crawlers AND search engine bots.
 * Intercepts /prediction/:id routes and adds dynamic meta tags + JSON-LD.
 */

// Use the direct Railway URL since api.fixturecast.com custom domain
// may not resolve from Cloudflare Pages functions
const BACKEND_API_URL = "https://backend-api-production-7b7d.up.railway.app";
const APP_URL = "https://fixturecast.com";

// NOTE: this Function used to run only for a hard-coded list of crawler user
// agents, serving everyone else the generic SPA shell. That meant search
// engines saw different markup to real people, and any sharing app not on the
// list produced a bare link preview. Meta tags are now built for every visitor.
// The cost is one backend lookup per page view, bounded by the timeout below,
// falling back to the plain app if it is slow or fails.

const FETCH_TIMEOUT_MS = 4000;

/**
 * Find a fixture by id, searching upcoming fixtures first and then recent
 * results.
 *
 * Why both: /api/fixtures only returns UPCOMING matches. Once a match kicks
 * off it disappears from that list. Search engines routinely crawl a page days
 * or weeks after discovering it, i.e. after the match has been played, so an
 * upcoming-only lookup silently failed for exactly the pages that had been
 * indexed longest. Those pages then rendered the placeholder title
 * "Home Team vs Away Team", which is unrankable and duplicated across
 * thousands of URLs.
 */
async function findFixture(fixtureId, leagueId) {
  const wanted = parseInt(fixtureId);
  if (!Number.isFinite(wanted)) return null;

  const endpoints = [
    `${BACKEND_API_URL}/api/fixtures?league=${leagueId}&next=50`,
    `${BACKEND_API_URL}/api/results?league=${leagueId}&last=50`,
  ];

  for (const endpoint of endpoints) {
    try {
      const res = await fetch(endpoint, {
        signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
      });
      if (!res.ok) continue;
      const data = await res.json();
      const found = data.response?.find((f) => f.fixture.id === wanted);
      if (found) return found;
    } catch {
      // Timeout or network error - try the next endpoint.
    }
  }

  return null;
}

export async function onRequest(context) {
  const { request, params, next } = context;

  // Extract fixture ID and league from URL.
  const fixtureId = params.id;
  const url = new URL(request.url);
  // No default league. Guessing "39" (Premier League) meant any link without
  // a ?league= tag looked the fixture up in the wrong competition, failed, and
  // fell back to the placeholder title.
  const leagueParam = url.searchParams.get("league");

  try {
    const fixture = leagueParam
      ? await findFixture(fixtureId, leagueParam)
      : null;

    // If we cannot identify the match, serve the plain app rather than
    // inventing a title. A generic page with the site's default title is far
    // better than thousands of pages all claiming to be "Home Team vs Away
    // Team".
    if (!fixture) {
      return next();
    }

    // Every field below comes from the fixture we actually found, so there are
    // no placeholder values left to leak into the title.
    const homeTeam = fixture.teams.home.name;
    const awayTeam = fixture.teams.away.name;
    const leagueName = fixture.league.name;
    const homeLogo = fixture.teams.home.logo || "";
    const awayLogo = fixture.teams.away.logo || "";
    const venueName = fixture.fixture.venue?.name || "Stadium";
    const matchDateISO = fixture.fixture.date;
    const matchDate = new Date(fixture.fixture.date).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });

    // Trust the fixture's own league rather than the query string.
    const leagueId = fixture.league.id;

    const ogImage = `${BACKEND_API_URL}/api/og-image/${fixtureId}?league=${leagueId}`;
    // The canonical KEEPS ?league=, because there is no per-fixture backend
    // endpoint - without a league we cannot look the match up, so a bare
    // /prediction/123 renders no meta tags at all. Pointing the canonical there
    // would aim search engines at the emptier version of the page.
    //
    // What this does fix: leagueId is taken from the fixture itself, so a link
    // carrying the wrong league (e.g. ?league=99) still emits the one correct
    // canonical, collapsing those variants into a single indexed URL.
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

    
    const metaTags = `
  <meta name="description" content="${description}">
  <meta name="keywords" content="${homeTeam} vs ${awayTeam} prediction, ${leagueName} predictions, football predictions, AI predictions">
  <link rel="canonical" href="${pageUrl}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="${pageUrl}">
  <meta property="og:title" content="${title}">
  <meta property="og:description" content="${description}">
  <meta property="og:image" content="${ogImage}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:site_name" content="FixtureCast">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:url" content="${pageUrl}">
  <meta name="twitter:title" content="${title}">
  <meta name="twitter:description" content="${description}">
  <meta name="twitter:image" content="${ogImage}">
  <meta name="twitter:site" content="@fixturecast">
  <script type="application/ld+json">${JSON.stringify(jsonLd)}</script>`;

    const response = await next();
    
    return new HTMLRewriter()
      .on("title", {
        element(e) {
          e.setInnerContent(title);
        }
      })
      .on("meta[name='description']", {
        element(e) {
          e.remove(); // remove default description
        }
      })
      .on("meta[name='keywords']", {
        element(e) {
          e.remove(); // remove default keywords
        }
      })
      // The base index.html ships its own og:* and twitter:* tags describing
      // the site as a whole. We append match-specific ones below, so without
      // this the page carries TWO of each. Crawlers differ on whether they take
      // the first or the last, and the site-wide ones come first - which is how
      // a shared match link ends up previewing as the generic
      // "FixtureCast - AI Football Predictions" with the default image.
      // Strip the defaults so only the match-specific tags survive.
      .on("meta[property^='og:']", {
        element(e) {
          e.remove();
        }
      })
      .on("meta[name^='twitter:']", {
        element(e) {
          e.remove();
        }
      })
      .on("link[rel='canonical']", {
        element(e) {
          e.remove(); // avoid two competing canonical URLs
        }
      })
      .on("head", {
        element(e) {
          e.append(metaTags, { html: true });
        }
      })
      .transform(response);

  } catch (error) {
    // On error, fall back to normal page
    console.error("Error generating OG page:", error);
    return next();
  }
}
