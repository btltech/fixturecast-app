/**
 * SEO Service
 * Generates optimized meta tags, structured data, and share images for predictions
 */

import { BACKEND_API_URL, APP_URL } from "../config.js";
import { LEAGUES } from "./leagues.js";

const SEO_DATE_LOCALES = {
  en: "en-US",
  es: "es-ES",
  pt: "pt-BR",
  fr: "fr-FR",
};

const SEO_COPY = {
  en: {
    home: {
      title: "FixtureCast - AI-Powered Football Match Predictions",
      description: `Free AI predictions for football matches across ${LEAGUES.length} competitions worldwide. Premier League, Champions League, La Liga, Serie A, Bundesliga, FIFA World Cup Qualifiers, Copa Libertadores, MLS, J1 League & more. Win probabilities, predicted scores, updated daily.`,
    },
    todays: {
      pageTitle: "Today's Fixtures",
      title: (today) => `Today's Fixtures - ${today}`,
      description: (today) => `All football matches playing today (${today}) with AI predictions, live scores, and detailed analysis.`,
    },
    dailyAccas: {
      title: "Daily Accumulator Tips",
      description: `AI-generated daily accumulator bets across ${LEAGUES.length} football competitions. 8-fold, 6-fold, 4-fold and BTTS accas built from high-confidence predictions — Premier League, La Liga, Copa Libertadores & more.`,
    },
    history: {
      title: "Prediction History",
      description: `Browse historical AI prediction results across ${LEAGUES.length} football competitions. Track model accuracy over time for Premier League, Champions League, La Liga, Copa Libertadores and more.`,
    },
    modelStats: {
      title: "AI Model Performance",
      description: "Track the accuracy and performance of our AI prediction system across different leagues and markets.",
    },
    prediction: {
      title: (homeTeam, awayTeam, dateStr) => `${homeTeam} vs ${awayTeam} Prediction - ${dateStr} | FixtureCast`,
      intro: (homeTeam, awayTeam, dateStr) => `AI prediction for ${homeTeam} vs ${awayTeam} on ${dateStr}. `,
      score: (score, homeTeam, homeProb, drawProb, awayTeam, awayProb) => `Predicted score: ${score}. Win probabilities: ${homeTeam} ${homeProb}%, Draw ${drawProb}%, ${awayTeam} ${awayProb}%.`,
      homeLabel: "Home",
      predictionsLabel: "Predictions",
      eventDescription: (league, homeTeam, awayTeam) => `${league} match between ${homeTeam} and ${awayTeam}`,
    },
  },
  es: {
    home: {
      title: "FixtureCast - Predicciones de fútbol con IA",
      description: `Predicciones gratuitas con IA para partidos de fútbol en ${LEAGUES.length} competiciones de todo el mundo. Premier League, Champions League, La Liga, Serie A, Bundesliga, eliminatorias mundialistas, Copa Libertadores, MLS, J1 League y más. Probabilidades de victoria, marcadores previstos y actualizaciones diarias.`,
    },
    todays: {
      pageTitle: "Partidos de hoy",
      title: (today) => `Partidos de hoy - ${today}`,
      description: (today) => `Todos los partidos de fútbol que se juegan hoy (${today}) con predicciones de IA, marcadores en vivo y análisis detallado.`,
    },
    dailyAccas: {
      title: "Combinadas diarias con IA",
      description: `Apuestas combinadas generadas por IA en ${LEAGUES.length} competiciones. Accas de 8, 6 y 4 selecciones, además de BTTS, construidas con predicciones de alta confianza.`,
    },
    history: {
      title: "Historial de predicciones",
      description: `Consulta resultados históricos de predicciones con IA en ${LEAGUES.length} competiciones de fútbol. Sigue la precisión del modelo a lo largo del tiempo para Premier League, Champions League, La Liga, Copa Libertadores y más.`,
    },
    modelStats: {
      title: "Rendimiento del sistema de IA",
      description: "Sigue la precisión y el rendimiento de nuestro sistema de predicción de IA en diferentes ligas y mercados.",
    },
    prediction: {
      title: (homeTeam, awayTeam, dateStr) => `Predicción de ${homeTeam} vs ${awayTeam} - ${dateStr} | FixtureCast`,
      intro: (homeTeam, awayTeam, dateStr) => `Predicción de IA para ${homeTeam} vs ${awayTeam} del ${dateStr}. `,
      score: (score, homeTeam, homeProb, drawProb, awayTeam, awayProb) => `Marcador previsto: ${score}. Probabilidades: ${homeTeam} ${homeProb}%, Empate ${drawProb}%, ${awayTeam} ${awayProb}%.`,
      homeLabel: "Inicio",
      predictionsLabel: "Predicciones",
      eventDescription: (league, homeTeam, awayTeam) => `Partido de ${league} entre ${homeTeam} y ${awayTeam}`,
    },
  },
  pt: {
    home: {
      title: "FixtureCast - Previsoes de futebol com IA",
      description: `Previsoes gratuitas com IA para partidas de futebol em ${LEAGUES.length} competicoes no mundo todo. Premier League, Champions League, La Liga, Serie A, Bundesliga, eliminatorias da Copa, Copa Libertadores, MLS, J1 League e mais. Probabilidades de vitoria, placares previstos e atualizacoes diarias.`,
    },
    todays: {
      pageTitle: "Jogos de hoje",
      title: (today) => `Jogos de hoje - ${today}`,
      description: (today) => `Todas as partidas de futebol de hoje (${today}) com previsoes de IA, placares ao vivo e analise detalhada.`,
    },
    dailyAccas: {
      title: "Acumuladores diarios com IA",
      description: `Apostas acumuladas geradas por IA em ${LEAGUES.length} competicoes. Accas de 8, 6 e 4 selecoes, alem de BTTS, montadas com previsoes de alta confianca.`,
    },
    history: {
      title: "Historico de previsoes",
      description: `Veja resultados historicos de previsoes com IA em ${LEAGUES.length} competicoes de futebol. Acompanhe a precisao do modelo ao longo do tempo para Premier League, Champions League, La Liga, Copa Libertadores e mais.`,
    },
    modelStats: {
      title: "Desempenho do sistema de IA",
      description: "Acompanhe a precisao e o desempenho do nosso sistema de previsao de IA em diferentes ligas e mercados.",
    },
    prediction: {
      title: (homeTeam, awayTeam, dateStr) => `Previsao de ${homeTeam} vs ${awayTeam} - ${dateStr} | FixtureCast`,
      intro: (homeTeam, awayTeam, dateStr) => `Previsao de IA para ${homeTeam} vs ${awayTeam} em ${dateStr}. `,
      score: (score, homeTeam, homeProb, drawProb, awayTeam, awayProb) => `Placar previsto: ${score}. Probabilidades: ${homeTeam} ${homeProb}%, Empate ${drawProb}%, ${awayTeam} ${awayProb}%.`,
      homeLabel: "Inicio",
      predictionsLabel: "Previsoes",
      eventDescription: (league, homeTeam, awayTeam) => `Partida de ${league} entre ${homeTeam} e ${awayTeam}`,
    },
  },
  fr: {
    home: {
      title: "FixtureCast - Predictions football par IA",
      description: `Predictions gratuites par IA pour des matchs de football dans ${LEAGUES.length} competitions a travers le monde. Premier League, Ligue des Champions, Liga, Serie A, Bundesliga, qualifications Coupe du Monde, Copa Libertadores, MLS, J1 League et plus encore. Probabilites de victoire, scores predicts et mises a jour quotidiennes.`,
    },
    todays: {
      pageTitle: "Matchs du jour",
      title: (today) => `Matchs du jour - ${today}`,
      description: (today) => `Tous les matchs de football d'aujourd'hui (${today}) avec predictions IA, scores en direct et analyse detaillee.`,
    },
    dailyAccas: {
      title: "Accumulateurs quotidiens IA",
      description: `Paris combines generes par IA sur ${LEAGUES.length} competitions. Accas 8, 6 et 4 selections ainsi que BTTS construits a partir de predictions a haute confiance.`,
    },
    history: {
      title: "Historique des predictions",
      description: `Consultez les resultats historiques des predictions IA sur ${LEAGUES.length} competitions de football. Suivez la precision du modele dans le temps pour la Premier League, la Ligue des Champions, la Liga, la Copa Libertadores et plus encore.`,
    },
    modelStats: {
      title: "Performance du systeme IA",
      description: "Suivez la precision et la performance de notre systeme de prediction IA sur differents championnats et marches.",
    },
    prediction: {
      title: (homeTeam, awayTeam, dateStr) => `Prediction ${homeTeam} vs ${awayTeam} - ${dateStr} | FixtureCast`,
      intro: (homeTeam, awayTeam, dateStr) => `Prediction IA pour ${homeTeam} vs ${awayTeam} le ${dateStr}. `,
      score: (score, homeTeam, homeProb, drawProb, awayTeam, awayProb) => `Score predit : ${score}. Probabilites : ${homeTeam} ${homeProb}%, Nul ${drawProb}%, ${awayTeam} ${awayProb}%.`,
      homeLabel: "Accueil",
      predictionsLabel: "Predictions",
      eventDescription: (league, homeTeam, awayTeam) => `Match de ${league} entre ${homeTeam} et ${awayTeam}`,
    },
  },
};

function normalizeSeoLocale(localeCode = "en") {
  const normalized = String(localeCode).toLowerCase().split("-")[0];
  return SEO_COPY[normalized] ? normalized : "en";
}

function getSeoCopy(localeCode = "en") {
  return SEO_COPY[normalizeSeoLocale(localeCode)];
}

function getSeoDateLocale(localeCode = "en") {
  return SEO_DATE_LOCALES[normalizeSeoLocale(localeCode)] || SEO_DATE_LOCALES.en;
}

function buildLocalizedAppUrl(path, localeCode = "en") {
  const url = new URL(path, APP_URL);
  const normalizedLocale = normalizeSeoLocale(localeCode);
  if (normalizedLocale === "en") {
    url.searchParams.delete("lang");
  } else {
    url.searchParams.set("lang", normalizedLocale);
  }
  return url.toString();
}

/**
 * Generate SEO metadata for a prediction page
 */
export function generatePredictionSEO(fixture, prediction, localeCode = "en") {
  const copy = getSeoCopy(localeCode).prediction;
  const homeTeam = fixture.teams?.home?.name || "Home Team";
  const awayTeam = fixture.teams?.away?.name || "Away Team";
  const league = fixture.league?.name || "League";
  const date = new Date(fixture.fixture?.date);
  const dateStr = date.toLocaleDateString(getSeoDateLocale(localeCode), {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  // Generate title (max 60 chars for Google)
  const title = copy.title(homeTeam, awayTeam, dateStr);

  // Generate description (max 160 chars for Google)
  let description = copy.intro(homeTeam, awayTeam, dateStr);

  if (prediction) {
    const homeProb = (prediction.home_win_prob * 100).toFixed(0);
    const awayProb = (prediction.away_win_prob * 100).toFixed(0);
    const drawProb = (prediction.draw_prob * 100).toFixed(0);
    const score = prediction.predicted_scoreline || "N/A";

    description += copy.score(
      score,
      homeTeam,
      homeProb,
      drawProb,
      awayTeam,
      awayProb,
    );
  }

  // Truncate description if too long
  if (description.length > 160) {
    description = description.substring(0, 157) + "...";
  }

  // Generate OG image URL (we'll create this endpoint)
  const fixtureId = fixture.fixture?.id;
  const leagueId = fixture.league?.id || 39;
  const imageUrl = `${BACKEND_API_URL}/api/og-image/${fixtureId}?league=${leagueId}`;

  // Page URL
  const url = buildLocalizedAppUrl(`/prediction/${fixtureId}?league=${leagueId}`, localeCode);

  // Generate Schema.org structured data
  const sportsEventSchema = generatePredictionSchema(fixture, prediction);
  const breadcrumbSchema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: copy.homeLabel, item: buildLocalizedAppUrl("/", localeCode) },
      { "@type": "ListItem", position: 2, name: copy.predictionsLabel, item: buildLocalizedAppUrl("/predictions", localeCode) },
      { "@type": "ListItem", position: 3, name: `${homeTeam} vs ${awayTeam}`, item: url },
    ],
  };

  return {
    title,
    description,
    image: imageUrl,
    url,
    type: "article",
    schema: [sportsEventSchema, breadcrumbSchema],
    keywords: generateKeywords(homeTeam, awayTeam, league),
  };
}

/**
 * Generate Schema.org structured data for prediction
 * https://schema.org/SportsEvent
 */
export function generatePredictionSchema(fixture, prediction, localeCode = "en") {
  const copy = getSeoCopy(localeCode).prediction;
  const homeTeam = fixture.teams?.home?.name || "Home Team";
  const awayTeam = fixture.teams?.away?.name || "Away Team";
  const league = fixture.league?.name || "League";
  const venue = fixture.fixture?.venue?.name || "Stadium";
  const date = fixture.fixture?.date;

  const schema = {
    "@context": "https://schema.org",
    "@type": "SportsEvent",
    name: `${homeTeam} vs ${awayTeam}`,
    description: copy.eventDescription(league, homeTeam, awayTeam),
    startDate: date,
    location: {
      "@type": "Place",
      name: venue,
    },
    homeTeam: {
      "@type": "SportsTeam",
      name: homeTeam,
      logo: fixture.teams?.home?.logo,
    },
    awayTeam: {
      "@type": "SportsTeam",
      name: awayTeam,
      logo: fixture.teams?.away?.logo,
    },
    sport: "Soccer",
    competitionCategory: league,
  };

  // Add prediction as additional metadata
  if (prediction) {
    schema.additionalProperty = [
      {
        "@type": "PropertyValue",
        name: "AI Predicted Score",
        value: prediction.predicted_scoreline,
      },
      {
        "@type": "PropertyValue",
        name: "Home Win Probability",
        value: `${(prediction.home_win_prob * 100).toFixed(1)}%`,
      },
      {
        "@type": "PropertyValue",
        name: "Draw Probability",
        value: `${(prediction.draw_prob * 100).toFixed(1)}%`,
      },
      {
        "@type": "PropertyValue",
        name: "Away Win Probability",
        value: `${(prediction.away_win_prob * 100).toFixed(1)}%`,
      },
    ];
  }

  return schema;
}

/**
 * Generate SEO keywords
 */
function generateKeywords(homeTeam, awayTeam, league) {
  return [
    `${homeTeam} vs ${awayTeam} prediction`,
    `${homeTeam} ${awayTeam} AI prediction`,
    `${league} predictions`,
    `${homeTeam} prediction`,
    `${awayTeam} prediction`,
    "football predictions",
    "soccer betting tips",
    "match predictions AI",
    "football AI",
  ].join(", ");
}

/**
 * Generate SEO for today's fixtures page
 */
export function generateFixturesSEO(localeCode = "en") {
  const today = new Date().toLocaleDateString(getSeoDateLocale(localeCode), {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  const copy = getSeoCopy(localeCode).todays;

  return {
    title: `${copy.pageTitle} — ${today} | FixtureCast`,
    description: copy.description(today),
    image: `${BACKEND_API_URL}/api/og-image/daily`,
    url: buildLocalizedAppUrl("/fixtures", localeCode),
    type: "website",
    keywords:
      "today's football predictions, soccer predictions today, AI football predictions, betting tips, match predictions, Premier League predictions today, Copa Libertadores predictions, MLS predictions, Bundesliga predictions",
  };
}

/**
 * Generate SEO for homepage
 */
export function generateHomeSEO(localeCode = "en") {
  const copy = getSeoCopy(localeCode).home;
  return {
    title: copy.title,
    description: copy.description,
    image: `${BACKEND_API_URL}/api/og-image/home`,
    url: buildLocalizedAppUrl("/", localeCode),
    type: "website",
    keywords:
      "football predictions, soccer predictions, AI predictions, Premier League predictions, Champions League predictions, FIFA World Cup predictions, Copa Libertadores predictions, MLS predictions, match predictions, betting tips, football AI, 90 leagues",
    schema: [
      {
        "@context": "https://schema.org",
        "@type": "WebSite",
        name: "FixtureCast",
        description: `AI-powered football match predictions across ${LEAGUES.length} competitions`,
        url: buildLocalizedAppUrl("/", localeCode),
      },
      {
        "@context": "https://schema.org",
        "@type": "Organization",
        name: "FixtureCast",
        url: buildLocalizedAppUrl("/", localeCode),
        logo: `${APP_URL}/icons/icon-192.png`,
        description: `AI-powered football match predictions across ${LEAGUES.length} competitions worldwide`,
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
  };
}

/**
 * Generate SEO-friendly URL slug
 */
export function generateSlug(homeTeam, awayTeam, date) {
  const dateStr = new Date(date).toISOString().split("T")[0]; // YYYY-MM-DD
  const slug = `${homeTeam}-vs-${awayTeam}-${dateStr}`
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  return slug;
}

/**
 * Generate generic page SEO metadata
 */
export function generatePageSEO(title, description, path = "/") {
  return {
    title: `${title} | FixtureCast`,
    description,
    image: `${BACKEND_API_URL}/api/og-image/home`,
    url: buildLocalizedAppUrl(path, "en"),
    type: "website",
    keywords: "football predictions, AI predictions, soccer predictions, match predictions",
  };
}

/**
 * Generate SEO for Live Scores page
 */
export function generateLiveScoresSEO() {
  return generatePageSEO(
    "Live Scores",
    `Follow live football scores and match updates across ${LEAGUES.length} competitions worldwide. Real-time results for Premier League, La Liga, Serie A, Champions League, FIFA World Cup Qualifiers, Copa Libertadores, MLS & more.`,
    "/live"
  );
}

/**
 * Generate SEO for Teams page
 */
export function generateTeamsSEO() {
  return generatePageSEO(
    "Football Team Statistics",
    `Detailed team statistics, form guides, and home/away records across ${LEAGUES.length} football competitions. Analyse any team from Premier League, La Liga, Serie A, Bundesliga, Copa Libertadores, MLS and more.`,
    "/teams"
  );
}

/**
 * Generate SEO for Standings page
 */
export function generateStandingsSEO() {
  return generatePageSEO(
    "League Standings & Tables",
    `Live league tables for ${LEAGUES.length} football competitions. Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, Europa League, Copa Libertadores, MLS, Russian Premier League & more — standings updated daily.`,
    "/standings"
  );
}

/**
 * Generate SEO for AI Predictions page
 */
export function generateMLPredictionsSEO() {
  return generatePageSEO(
    "AI Match Predictions",
    `AI-powered football predictions with win probabilities and predicted scores. Covering ${LEAGUES.length} competitions including Premier League, La Liga, Serie A, Bundesliga, Champions League, FIFA World Cup Qualifiers, Copa Libertadores and MLS.`,
    "/predictions"
  );
}

/**
 * Generate SEO for Smart Markets page
 */
export function generateSmartMarketsSEO() {
  return generatePageSEO(
    "Smart Markets — AI Value Bets",
    `AI-identified value bets where we beat the market. Over/Under 2.5 goals and BTTS predictions with 60%+ confidence. Only real-edge picks across ${LEAGUES.length} football competitions.`,
    "/smart-markets"
  );
}

/**
 * Generate SEO for Daily Accumulators page
 */
export function generateDailyAccasSEO(localeCode = "en") {
  const copy = getSeoCopy(localeCode).dailyAccas;
  return {
    ...generatePageSEO(copy.title, copy.description, "/accumulators"),
    url: buildLocalizedAppUrl("/accumulators", localeCode),
  };
}

export function generateHistorySEO(localeCode = "en") {
  const copy = getSeoCopy(localeCode).history;
  return {
    ...generatePageSEO(copy.title, copy.description, "/history"),
    url: buildLocalizedAppUrl("/history", localeCode),
  };
}

/**
 * Generate SEO for Results page
 */
export function generateResultsSEO(localeCode = "en") {
  return generatePageSEO(
    "Football Results",
    `Latest football match results and final scores across ${LEAGUES.length} competitions. Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, Europa League, FIFA World Cup Qualifiers & Copa Libertadores results updated daily.`,
    "/results"
  );
}

/**
 * Generate SEO for Model Stats page
 */
export function generateModelStatsSEO(localeCode = "en") {
  const copy = getSeoCopy(localeCode).modelStats;
  return {
    ...generatePageSEO(copy.title, copy.description, "/models"),
    url: buildLocalizedAppUrl("/models", localeCode),
  };
}

/**
 * Generate dynamic SEO for a Team detail page
 */
export function generateTeamSEO(teamData) {
  const teamName = teamData?.team?.name || "Team";
  const country = teamData?.team?.country || "";
  const logo = teamData?.team?.logo;
  const teamId = teamData?.team?.id;
  return {
    title: `${teamName} — Stats, Form & Predictions | FixtureCast`,
    description: `${teamName} statistics, form guide, squad, fixtures and AI predictions${country ? ` (${country})` : ""}. Win rates, scoring trends and upcoming match analysis — updated daily.`,
    image: logo || `${BACKEND_API_URL}/api/og-image/home`,
    url: teamId ? `${APP_URL}/team/${teamId}` : `${APP_URL}/teams`,
    type: "website",
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

/**
 * Generate SEO for a League landing page
 */
export function generateLeagueSEO(league) {
  const { id, name, country, emoji, tier } = league;
  const tierLabel =
    tier === 0 ? "FIFA/Continental" :
    tier === 1 ? "Top Division" :
    tier === 2 ? "Second Division" :
    tier === 3 ? "Cup Competition" : "Football";
  const countryStr = country && country !== "World" ? country : "";
  return {
    title: `${emoji} ${name} Predictions, Fixtures & Standings | FixtureCast`,
    description: `AI-powered ${name} predictions, upcoming fixtures, live standings and results. ${countryStr ? `${countryStr} ${tierLabel}` : tierLabel} — all matches covered by FixtureCast's ML engine. Updated daily.`,
    image: `${BACKEND_API_URL}/api/og-image/home`,
    url: `${APP_URL}/league/${id}`,
    type: "website",
    keywords: `${name} predictions, ${name} fixtures, ${name} standings, ${countryStr ? countryStr + " football" : "football"} predictions, AI football predictions`,
    schema: [
      {
        "@context": "https://schema.org",
        "@type": "SportsOrganization",
        name,
        sport: "Soccer",
        ...(countryStr ? { location: { "@type": "Place", name: countryStr } } : {}),
      },
      {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: APP_URL },
          { "@type": "ListItem", position: 2, name: "Predictions", item: `${APP_URL}/predictions` },
          { "@type": "ListItem", position: 3, name, item: `${APP_URL}/league/${id}` },
        ],
      },
    ],
  };
}

/**
 * Generate SEO for Today's Fixtures page
 */
export function generateTodaysFixturesSEO(localeCode = "en") {
  const today = new Date().toLocaleDateString(getSeoDateLocale(localeCode), {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
  const copy = getSeoCopy(localeCode).todays;
  return {
    ...generatePageSEO(copy.title(today), copy.description(today), "/today"),
    url: buildLocalizedAppUrl("/today", localeCode),
  };
}

