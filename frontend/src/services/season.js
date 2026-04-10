// Centralized season helpers for the app.
// Cross-year domestic competitions use the season start year.
// Calendar-year competitions (MLS, World Cup, qualifiers, etc.) use the fixture year.

export const CALENDAR_YEAR_LEAGUE_IDS = new Set([
  1, 15, 16, 17, 22, 29, 30, 31, 32, 34, 6, 5,
  11, 12, 13, 71, 73, 98, 116, 128, 130, 164, 169, 183,
  239, 244, 253, 255, 262, 265, 278, 292, 296, 323, 340,
]);

function normalizeDate(dateLike = new Date()) {
  if (dateLike instanceof Date) {
    return dateLike;
  }

  const parsed = new Date(dateLike);
  return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
}

function getCrossYearSeason(dateLike = new Date()) {
  const envSeason = Number(import.meta.env.VITE_SEASON);
  if (!Number.isNaN(envSeason) && envSeason > 1900) {
    return envSeason;
  }

  const date = normalizeDate(dateLike);
  const year = date.getFullYear();
  const month = date.getMonth();

  // Cross-year leagues tick over in July and are labeled by the starting year.
  return month >= 6 ? year : year - 1;
}

export function getCurrentSeason(dateLike = new Date()) {
  return getCrossYearSeason(dateLike);
}

export function isCalendarYearLeague(leagueId) {
  const id = typeof leagueId === "string" ? parseInt(leagueId, 10) : leagueId;
  return CALENDAR_YEAR_LEAGUE_IDS.has(id);
}

export function getLeagueSeason(leagueId, dateLike = new Date()) {
  const date = normalizeDate(dateLike);
  return isCalendarYearLeague(leagueId) ? date.getFullYear() : getCrossYearSeason(date);
}
