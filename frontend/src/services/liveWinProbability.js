/**
 * Live (in-play) win probability — a cheap analytic model.
 *
 * It reuses the *pre-match* prediction's full-match goal expectation (recovered
 * from its `scoreline_distribution`) and conditions on the CURRENT score and the
 * minutes remaining. There is no new model and no network call: it's pure
 * deterministic math, recomputed on each refresh tick from data already fetched.
 *
 * Assumptions (first-order in-play model):
 *  - a roughly uniform scoring rate across 90 minutes, and
 *  - independent Poisson goals for the remainder of the match.
 * It does NOT see momentum, xG, or tactical changes — but it is far more honest
 * than showing a frozen pre-match percentage on a live page, and it costs
 * essentially nothing to run. An optional red-card adjustment nudges the rates.
 */

const REGULATION_MINUTES = 90;
const FINISHED = new Set(["FT", "AET", "PEN"]);

function poissonPmf(k, lambda) {
  if (lambda <= 0) return k === 0 ? 1 : 0;
  // exp(-lambda) * lambda^k / k!  (iterative, avoids factorial overflow)
  let p = Math.exp(-lambda);
  for (let i = 1; i <= k; i++) p = (p * lambda) / i;
  return p;
}

/**
 * Recover full-match expected goals (home, away) from a scoreline distribution
 * map like { "0-0": 278, "2-1": 733, ... } (raw weights or probabilities).
 * Returns null if the map is missing or unusable.
 */
export function lambdasFromDistribution(dist) {
  if (!dist || typeof dist !== "object") return null;
  let total = 0;
  let sumHome = 0;
  let sumAway = 0;
  for (const key of Object.keys(dist)) {
    const w = Number(dist[key]);
    if (!Number.isFinite(w) || w < 0) continue;
    const m = /^(\d+)\s*-\s*(\d+)$/.exec(key);
    if (!m) continue;
    const h = parseInt(m[1], 10);
    const a = parseInt(m[2], 10);
    total += w;
    sumHome += w * h;
    sumAway += w * a;
  }
  if (total <= 0) return null;
  return { home: sumHome / total, away: sumAway / total };
}

/**
 * Live 1X2 probabilities conditional on the current score and time elapsed.
 *
 * @param {object}  opts
 * @param {object}  opts.prediction     pre-match prediction (uses scoreline_distribution)
 * @param {number}  opts.homeGoals      current home goals
 * @param {number}  opts.awayGoals      current away goals
 * @param {number}  opts.elapsed        minutes played
 * @param {string}  opts.statusShort    API status code (1H/HT/2H/FT/…)
 * @param {number} [opts.homeRed]       home red cards (incl. 2nd yellows)
 * @param {number} [opts.awayRed]       away red cards
 * @param {number} [opts.maxGoals]      grid size for remaining goals
 * @returns {{home:number, draw:number, away:number, fracRemaining:number}|null}
 */
export function liveWinProbabilities({
  prediction,
  homeGoals = 0,
  awayGoals = 0,
  elapsed = 0,
  statusShort = "",
  homeRed = 0,
  awayRed = 0,
  maxGoals = 10,
}) {
  if (!prediction) return null;

  const h = Math.max(0, Math.floor(homeGoals || 0));
  const a = Math.max(0, Math.floor(awayGoals || 0));

  // Concluded match → the result is decided; return a deterministic outcome.
  if (FINISHED.has(String(statusShort).toUpperCase())) {
    return {
      home: h > a ? 1 : 0,
      draw: h === a ? 1 : 0,
      away: h < a ? 1 : 0,
      fracRemaining: 0,
    };
  }

  const lambdas = lambdasFromDistribution(prediction.scoreline_distribution);
  if (!lambdas) return null;

  const minutesLeft = Math.min(
    REGULATION_MINUTES,
    Math.max(0, REGULATION_MINUTES - (elapsed || 0)),
  );
  const frac = minutesLeft / REGULATION_MINUTES;

  // Remaining expected goals, scaled by time left, with a modest red-card tweak:
  // a sent-off team scores a bit less and concedes a bit more.
  const redFactor = (own, opp) =>
    Math.pow(0.75, Math.max(0, own)) * Math.pow(1.1, Math.max(0, opp));
  const remHome = lambdas.home * frac * redFactor(homeRed, awayRed);
  const remAway = lambdas.away * frac * redFactor(awayRed, homeRed);

  // Independent Poisson distributions of REMAINING goals for each side.
  const ph = new Array(maxGoals + 1);
  const pa = new Array(maxGoals + 1);
  let chh = 0;
  let cha = 0;
  for (let k = 0; k <= maxGoals; k++) {
    ph[k] = poissonPmf(k, remHome);
    pa[k] = poissonPmf(k, remAway);
    chh += ph[k];
    cha += pa[k];
  }
  // Park any truncated tail mass on the top bucket so each side sums to 1.
  ph[maxGoals] += Math.max(0, 1 - chh);
  pa[maxGoals] += Math.max(0, 1 - cha);

  let pHome = 0;
  let pDraw = 0;
  let pAway = 0;
  for (let x = 0; x <= maxGoals; x++) {
    for (let y = 0; y <= maxGoals; y++) {
      const prob = ph[x] * pa[y];
      const finalHome = h + x;
      const finalAway = a + y;
      if (finalHome > finalAway) pHome += prob;
      else if (finalHome === finalAway) pDraw += prob;
      else pAway += prob;
    }
  }

  const s = pHome + pDraw + pAway || 1;
  return {
    home: pHome / s,
    draw: pDraw / s,
    away: pAway / s,
    fracRemaining: frac,
  };
}

/**
 * Leading outcome from a {home,draw,away} probability triple.
 * Returns prob as a percentage (×100) to match the existing card badges.
 */
export function leadingOutcome(probs) {
  if (!probs) return null;
  const { home = 0, draw = 0, away = 0 } = probs;
  if (home >= draw && home >= away)
    return { winner: "home", prob: home * 100, label: "Home" };
  if (away >= home && away >= draw)
    return { winner: "away", prob: away * 100, label: "Away" };
  return { winner: "draw", prob: draw * 100, label: "Draw" };
}
