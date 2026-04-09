// Centralized league metadata for FixtureCast.
// The authoritative data lives in /data/leagues.json — this file re-exports it
// with helper functions. Do NOT add leagues inline here; edit leagues.json instead.

import LEAGUES_DATA from "../../../data/leagues.json";

/** @type {Array<{id: number, name: string, country: string, emoji: string, tier: number}>} */
export const LEAGUES = LEAGUES_DATA;

const LEAGUE_BY_ID = new Map(LEAGUES.map((l) => [l.id, l]));

export function getLeague(leagueId) {
  const id = typeof leagueId === "string" ? parseInt(leagueId, 10) : leagueId;
  return LEAGUE_BY_ID.get(id) || null;
}

export function getLeagueDisplay(leagueId) {
  const league = getLeague(leagueId);
  return league
    ? { name: league.name, emoji: league.emoji }
    : { name: "League", emoji: "⚽" };
}

export function leaguesByTier(tier) {
  return LEAGUES.filter((l) => l.tier === tier);
}

// Featured leagues in priority order (used for sorting/grouping in UI).
export const FEATURED_LEAGUE_IDS = [
  // FIFA & Confederation events (shown when active)
  1,   // FIFA World Cup
  15,  // FIFA Club World Cup
  17,  // AFC Champions League Elite
  16,  // CONCACAF Champions Cup
  22,  // CONCACAF Gold Cup
  6,   // AFCON
  29, 30, 31, 32, 34, // World Cup Qualifiers
  39, // Premier League
  140, // La Liga
  135, // Serie A
  78, // Bundesliga
  61, // Ligue 1
  2, // UEFA Champions League
  3, // UEFA Europa League
  848, // UEFA Conference League
  88, // Eredivisie
  94, // Primeira Liga
  218, // Austrian Bundesliga
  207, // Swiss Super League
  119, // Danish Superliga
  113, // Allsvenskan
  103, // Eliteserien
  307, // Saudi Pro League
  253, // MLS
  203, // Süper Lig
  71, // Brasileirão
  179, // Scottish Premiership
  144, // Belgian Pro League
  // Expansion — Americas & Asia
  128, // Argentine Primera División
  262, // Liga MX
  98, // J1 League
  239, // Colombian Primera A
  265, // Chilean Primera
  292, // K League 1
  323, // Indian Super League
  435, // UAE Pro League
  // Expansion — Africa
  233, // Egyptian Premier League
  289, // South African PSL
  200, // Moroccan Botola Pro
  213, // Tunisian Ligue 1
  198, // Algerian Ligue Pro 1
  332, // Nigerian Pro League
  338, // Ghanaian Premier League
  // Expansion — Europe
  197, // Greek Super League
  106, // Polish Ekstraklasa
  271, // Israeli Premier League
  283, // Romanian Liga 1
  345, // Czech First League
  // High-scoring small leagues
  116, // Faroese Premier League
  183, // Maltese Premier League
  244, // Finnish Veikkausliiga
  164, // Icelandic Úrvalsdeild
  169, // Chinese Super League
  // New 2026 expansion
  5,   // UEFA Nations League
  13,  // Copa Libertadores
  11,  // Copa Sudamericana
  12,  // CAF Champions League
  41,  // League One
  42,  // League Two
  43,  // National League
  235, // Russian Premier League
  333, // Ukrainian Premier League
  210, // Croatian HNL
  286, // Serbian SuperLiga
  188, // A-League
  296, // Thai League 1
  278, // Malaysian Super League
  340, // Vietnam V-League 1
  255, // USL Championship
  81,  // DFB-Pokal
  137, // Coppa Italia
  143, // Copa del Rey
  66,  // Coupe de France
  181, // Scottish FA Cup
  73,  // Copa do Brasil
  130, // Copa Argentina
  46,  // EFL Trophy
];
