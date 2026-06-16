// Unit tests for liveWinProbability.js — run: node tests/test_live_win_prob.mjs
import {
  lambdasFromDistribution,
  liveWinProbabilities,
  leadingOutcome,
} from "../src/services/liveWinProbability.js";

let pass = 0;
let fail = 0;
function ok(name, cond) {
  if (cond) {
    pass++;
    console.log("  ✓", name);
  } else {
    fail++;
    console.error("  ✗", name);
  }
}
const approx = (x, y, tol = 1e-6) => Math.abs(x - y) <= tol;

// Build a synthetic scoreline_distribution from two Poisson lambdas so that
// lambdasFromDistribution should recover (≈) those lambdas.
function distFromLambdas(lh, la, max = 10) {
  const pois = (k, l) => {
    let p = Math.exp(-l);
    for (let i = 1; i <= k; i++) p = (p * l) / i;
    return p;
  };
  const d = {};
  for (let i = 0; i <= max; i++)
    for (let j = 0; j <= max; j++) d[`${i}-${j}`] = pois(i, lh) * pois(j, la);
  return d;
}

console.log("lambdasFromDistribution:");
ok("single 1-0 → home 1, away 0", (() => {
  const l = lambdasFromDistribution({ "1-0": 1 });
  return approx(l.home, 1) && approx(l.away, 0);
})());
ok("mix 0-0 & 2-2 → home 1, away 1", (() => {
  const l = lambdasFromDistribution({ "0-0": 1, "2-2": 1 });
  return approx(l.home, 1) && approx(l.away, 1);
})());
ok("recovers Poisson means (1.6 / 1.1)", (() => {
  const l = lambdasFromDistribution(distFromLambdas(1.6, 1.1));
  return approx(l.home, 1.6, 1e-3) && approx(l.away, 1.1, 1e-3);
})());
ok("null/garbage → null", lambdasFromDistribution(null) === null && lambdasFromDistribution({}) === null);

const pred = { scoreline_distribution: distFromLambdas(1.5, 1.1) };
const sums1 = (p) => approx(p.home + p.draw + p.away, 1, 1e-9);

console.log("liveWinProbabilities — determinism on finished matches:");
ok("FT 2-1 → home=1", (() => {
  const p = liveWinProbabilities({ prediction: pred, homeGoals: 2, awayGoals: 1, statusShort: "FT" });
  return p.home === 1 && p.draw === 0 && p.away === 0;
})());
ok("FT 2-2 → draw=1", (() => {
  const p = liveWinProbabilities({ prediction: pred, homeGoals: 2, awayGoals: 2, statusShort: "FT" });
  return p.draw === 1;
})());
ok("AET 0-1 → away=1", (() => {
  const p = liveWinProbabilities({ prediction: pred, homeGoals: 0, awayGoals: 1, statusShort: "AET" });
  return p.away === 1;
})());

console.log("liveWinProbabilities — in-play behaviour:");
const kickoff = liveWinProbabilities({ prediction: pred, homeGoals: 0, awayGoals: 0, elapsed: 0, statusShort: "1H" });
ok("kickoff probs sum to 1", sums1(kickoff));
ok("kickoff: home favoured (λ 1.5 vs 1.1)", kickoff.home > kickoff.away);

const lead30 = liveWinProbabilities({ prediction: pred, homeGoals: 2, awayGoals: 0, elapsed: 30, statusShort: "1H" });
const lead85 = liveWinProbabilities({ prediction: pred, homeGoals: 2, awayGoals: 0, elapsed: 85, statusShort: "2H" });
ok("2-0 lead: prob rises as time runs down (85' > 30')", lead85.home > lead30.home);
ok("2-0 at 85' is near-certain (>0.95)", lead85.home > 0.95);
ok("lead85 sums to 1", sums1(lead85));

const awayLate = liveWinProbabilities({ prediction: pred, homeGoals: 0, awayGoals: 1, elapsed: 88, statusShort: "2H" });
ok("0-1 at 88' → away strongly favoured (>0.9)", awayLate.away > 0.9);

console.log("liveWinProbabilities — red-card adjustment:");
const noRed = liveWinProbabilities({ prediction: pred, homeGoals: 1, awayGoals: 1, elapsed: 60, statusShort: "2H" });
const awaySentOff = liveWinProbabilities({ prediction: pred, homeGoals: 1, awayGoals: 1, elapsed: 60, statusShort: "2H", awayRed: 1 });
ok("away red card raises home win prob", awaySentOff.home > noRed.home);
ok("red-card case still sums to 1", sums1(awaySentOff));

console.log("liveWinProbabilities — guards:");
ok("no prediction → null", liveWinProbabilities({ prediction: null, statusShort: "1H" }) === null);
ok("no distribution → null", liveWinProbabilities({ prediction: { scoreline_distribution: null }, statusShort: "1H" }) === null);

console.log("leadingOutcome:");
ok("picks home", (() => { const r = leadingOutcome({ home: 0.6, draw: 0.25, away: 0.15 }); return r.winner === "home" && approx(r.prob, 60); })());
ok("picks away", leadingOutcome({ home: 0.2, draw: 0.3, away: 0.5 }).winner === "away");
ok("null → null", leadingOutcome(null) === null);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
