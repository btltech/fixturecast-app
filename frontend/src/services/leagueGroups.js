// Single source of truth for how leagues are grouped in every selector
// (Fixtures sidebar, Results / Standings chip grids, the AI predictions dropdown).
//
// Previously each page re-implemented `leagues.filter(l => l.tier === N)` with its own
// label and emoji, which is how the group labels/ordering drifted apart (e.g. tier-0
// being called "European Competitions" on some pages). Consume `getLeagueGroups()`
// instead so the structure and labels can never diverge again.
//
// `labelKey` resolves against the shared i18n block `leagueGroups.*`.

export const LEAGUE_GROUPS = [
  { tier: 0, key: "cupsInternationals", emoji: "🏆", labelKey: "leagueGroups.cupsInternationals" },
  { tier: 1, key: "topLeagues", emoji: "⭐", labelKey: "leagueGroups.topLeagues" },
  { tier: 2, key: "moreLeagues", emoji: "📋", labelKey: "leagueGroups.moreLeagues" },
  { tier: 3, key: "domesticCups", emoji: "🥇", labelKey: "leagueGroups.domesticCups" },
];

/**
 * Group a list of leagues into the canonical, ordered groups.
 * @param {Array<{id:number, tier:number}>} leagues
 * @param {{ filterIds?: Set<number>|null }} [opts] - optionally restrict to active league ids
 * @returns {Array<{tier:number, key:string, emoji:string, labelKey:string, leagues:Array}>}
 *          only groups that actually contain leagues, in canonical order.
 */
export function getLeagueGroups(leagues, opts = {}) {
  const { filterIds = null } = opts;
  const list = Array.isArray(leagues) ? leagues : [];
  return LEAGUE_GROUPS.map((group) => ({
    ...group,
    leagues: list.filter(
      (l) => l && l.tier === group.tier && (!filterIds || filterIds.has(l.id)),
    ),
  })).filter((group) => group.leagues.length > 0);
}
