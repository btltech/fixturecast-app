import LEAGUES_DATA from "../../../data/leagues.json";

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

async function fetchTeam(teamId, leagueId) {
  const search = new URLSearchParams({ id: String(teamId) });
  if (leagueId) {
    search.set("league", String(leagueId));
  }

  try {
    const response = await fetch(
      `${BACKEND_API_URL}/api/teams?${search.toString()}`,
      { signal: AbortSignal.timeout(5000) },
    );
    if (!response.ok) return null;

    const data = await response.json();
    if (!Array.isArray(data.response) || !data.response.length) {
      return null;
    }

    return data.response.find((item) => item.team?.id === teamId) || data.response[0];
  } catch {
    return null;
  }
}

async function fetchUpcomingFixtures(teamId, leagueId) {
  if (!leagueId) return [];

  try {
    const response = await fetch(
      `${BACKEND_API_URL}/api/team/${encodeURIComponent(teamId)}/upcoming?league=${encodeURIComponent(leagueId)}&next=3`,
      { signal: AbortSignal.timeout(5000) },
    );
    if (!response.ok) return [];

    const data = await response.json();
    return Array.isArray(data.response) ? data.response.slice(0, 3) : [];
  } catch {
    return [];
  }
}

function buildTeamSeo(teamData) {
  const teamName = teamData?.team?.name || "Team";
  const country = teamData?.team?.country || "";
  const logo = teamData?.team?.logo;
  const teamId = teamData?.team?.id;

  return {
    title: `${teamName} — Stats, Form & Predictions | FixtureCast`,
    description: `${teamName} statistics, form guide, squad, fixtures and AI predictions${country ? ` (${country})` : ""}. Win rates, scoring trends and upcoming match analysis — updated daily.`,
    image: logo || `${BACKEND_API_URL}/api/og-image/home`,
    url: teamId ? `${APP_URL}/team/${teamId}` : `${APP_URL}/teams`,
    keywords: `${teamName} predictions, ${teamName} stats, ${teamName} form, football predictions`,
    schema: {
      "@context": "https://schema.org",
      "@type": "SportsTeam",
      name: teamName,
      sport: "Soccer",
      ...(logo ? { logo } : {}),
      ...(country ? { location: { "@type": "Place", name: country } } : {}),
    },
  };
}

function buildUpcomingMarkup(fixtures, leagueId) {
  if (!fixtures.length) {
    return "<p>Upcoming fixtures will appear here when this team has published matches in the selected competition.</p>";
  }

  const items = fixtures
    .map((fixture) => {
      const fixtureId = fixture.fixture?.id;
      const homeName = fixture.teams?.home?.name || "Home Team";
      const awayName = fixture.teams?.away?.name || "Away Team";
      const href = `${APP_URL}/prediction/${fixtureId}?league=${leagueId}`;

      return `<li><a href="${escapeHtml(href)}">${escapeHtml(homeName)} vs ${escapeHtml(awayName)}</a> <span>${escapeHtml(formatDate(fixture.fixture?.date))}</span></li>`;
    })
    .join("\n");

  return `<ul>${items}</ul>`;
}

function buildBody(teamData, seo, league) {
  const teamName = teamData?.team?.name || "Team";
  const country = teamData?.team?.country || "";
  const venue = teamData?.venue?.name || "";
  const founded = teamData?.team?.founded || "";

  return `<main>
  <header>
    <h1>${escapeHtml(`${teamName} Stats, Form & Predictions`)}</h1>
    <p>${escapeHtml(seo.description)}</p>
    ${country ? `<p>Country: ${escapeHtml(country)}</p>` : ""}
    ${venue ? `<p>Home venue: ${escapeHtml(venue)}</p>` : ""}
    ${founded ? `<p>Founded: ${escapeHtml(founded)}</p>` : ""}
    ${league ? `<p>Competition context: <a href="${escapeHtml(`${APP_URL}/league/${league.id}`)}">${escapeHtml(league.name)}</a></p>` : ""}
  </header>

  <nav>
    <p><a href="${escapeHtml(seo.url)}">Open ${escapeHtml(teamName)} on FixtureCast</a></p>
    <p><a href="${escapeHtml(`${APP_URL}/teams`)}">Browse more football teams</a></p>
  </nav>
</main>`;
}

function appendUpcomingSection(body, fixtures, leagueId, teamName) {
  if (!leagueId) {
    return `${body}\n<section><h2>Upcoming fixtures</h2><p>Upcoming fixtures appear here when this team is associated with a supported competition on FixtureCast.</p></section>`;
  }

  return `${body}\n<section><h2>Upcoming ${escapeHtml(teamName)} fixtures</h2>${buildUpcomingMarkup(fixtures, leagueId)}</section>`;
}

export async function onRequest(context) {
  const { request, params, next } = context;
  const userAgent = request.headers.get("user-agent") || "";

  if (!isCrawler(userAgent)) {
    return next();
  }

  const teamId = parseInt(params.id, 10);
  if (!Number.isFinite(teamId)) {
    return next();
  }

  const url = new URL(request.url);
  const leagueId = url.searchParams.get("league");
  const league = leagueId ? LEAGUE_BY_ID.get(String(leagueId)) : null;

  try {
    const [teamData, upcomingFixtures] = await Promise.all([
      fetchTeam(teamId, leagueId),
      fetchUpcomingFixtures(teamId, leagueId),
    ]);

    if (!teamData?.team?.id) {
      return next();
    }

    const seo = buildTeamSeo(teamData);
    const html = buildHtml({
      ...seo,
      body: appendUpcomingSection(
        buildBody(teamData, seo, league),
        upcomingFixtures,
        leagueId,
        teamData.team.name || "Team",
      ),
    });

    return new Response(html, {
      headers: {
        "content-type": "text/html;charset=UTF-8",
        "cache-control": "public, max-age=3600",
      },
    });
  } catch (error) {
    console.error("Error generating team crawler page:", error);
    return next();
  }
}