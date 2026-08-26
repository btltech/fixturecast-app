/**
 * Detect score changes between live-scores refreshes, so the UI can flash a card
 * when a goal goes in. Pure functions — no DOM, no state of their own.
 */

/** Compact score key for a match, or null if the score isn't known yet. */
export function scoreKey(match) {
  const h = match?.goals?.home ?? null;
  const a = match?.goals?.away ?? null;
  return h === null && a === null ? null : `${h}-${a}`;
}

/**
 * Compare the previous score map to the latest matches.
 * @returns {{ next: Record<string,string|null>, changed: number[] }}
 *   `next` is the new score map to store; `changed` lists fixture ids whose
 *   score changed since last time (first sighting never counts as a change).
 */
export function detectScoreChanges(prev, matches) {
  const next = {};
  const changed = [];
  for (const m of matches || []) {
    const id = m?.fixture?.id;
    if (id == null) continue;
    const key = scoreKey(m);
    next[id] = key;
    const before = prev ? prev[id] : undefined;
    if (before !== undefined && key !== null && before !== null && before !== key) {
      changed.push(id);
    }
  }
  return { next, changed };
}
