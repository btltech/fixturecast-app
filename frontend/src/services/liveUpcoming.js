/**
 * Helpers for the "Starting soon" strip on the Live Scores page: pick today's
 * not-yet-started fixtures and format a countdown to kick-off. Pure functions.
 */

/** Today's not-started fixtures, soonest first, capped at `limit`. */
export function selectUpcoming(fixtures, limit = 10) {
  return (fixtures || [])
    .filter((f) => f?.fixture?.status?.short === "NS")
    .sort(
      (a, b) =>
        (a?.fixture?.timestamp ?? Infinity) - (b?.fixture?.timestamp ?? Infinity),
    )
    .slice(0, Math.max(0, limit));
}

/** Human countdown to kick-off, e.g. "in 2h 14m", "in 8m", "kicking off". */
export function kickoffIn(dateStr, nowMs) {
  const t = new Date(dateStr).getTime();
  if (!t || Number.isNaN(t)) return "";
  const diff = Math.floor((t - nowMs) / 1000);
  if (diff <= 0) return "kicking off";
  const h = Math.floor(diff / 3600);
  const m = Math.floor((diff % 3600) / 60);
  if (h > 0) return `in ${h}h ${m}m`;
  if (m > 0) return `in ${m}m`;
  return "in <1m";
}
