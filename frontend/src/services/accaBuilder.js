// Pure accumulator math for the bet-slip builder.
//
// A selection carries a model probability (0–1) and, when the market is available,
// decimal odds. When odds are missing we fall back to *fair* odds = 1 / prob.
//
// combinedProb  — model probability that ALL legs land (product of leg probabilities).
// combinedOdds  — product of each leg's decimal odds (book odds where available).
// fairOdds      — 1 / combinedProb (what the odds "should" be on the model).
// An accumulator has positive expected value when combinedOdds > fairOdds.

export function selectionOdds(sel) {
  if (sel && typeof sel.odds === "number" && sel.odds > 1) return sel.odds;
  const p = sel && typeof sel.prob === "number" ? sel.prob : 0;
  return p > 0 ? 1 / p : 0;
}

export function accaSummary(selections) {
  const list = Array.isArray(selections) ? selections : [];
  if (list.length === 0) {
    return { count: 0, combinedProb: 0, combinedOdds: 0, fairOdds: 0, hasEdge: false };
  }
  let combinedProb = 1;
  let combinedOdds = 1;
  for (const s of list) {
    const p = Math.min(Math.max(Number(s.prob) || 0, 0), 1);
    combinedProb *= p;
    combinedOdds *= selectionOdds(s);
  }
  const fairOdds = combinedProb > 0 ? 1 / combinedProb : 0;
  return {
    count: list.length,
    combinedProb,
    combinedOdds,
    fairOdds,
    // Only meaningful when at least one leg had real book odds.
    hasEdge: combinedOdds > fairOdds && fairOdds > 0,
  };
}

export function potentialReturn(stake, combinedOdds) {
  const s = Number(stake) || 0;
  const o = Number(combinedOdds) || 0;
  return s > 0 && o > 0 ? s * o : 0;
}
