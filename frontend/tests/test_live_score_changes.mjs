// Tests for liveScoreChanges.js — run: node tests/test_live_score_changes.mjs
import { scoreKey, detectScoreChanges } from "../src/services/liveScoreChanges.js";

let pass = 0, fail = 0;
const ok = (n, c) => (c ? (pass++, console.log("  ✓", n)) : (fail++, console.error("  ✗", n)));
const mk = (id, h, a) => ({ fixture: { id }, goals: { home: h, away: a } });

ok("scoreKey 1-0", scoreKey(mk(1, 1, 0)) === "1-0");
ok("scoreKey null when no goals", scoreKey({ fixture: { id: 1 }, goals: { home: null, away: null } }) === null);

// First sighting never flashes.
let r = detectScoreChanges({}, [mk(1, 0, 0), mk(2, 1, 0)]);
ok("first load → no changes", r.changed.length === 0);
ok("first load → builds next map", r.next[1] === "0-0" && r.next[2] === "1-0");

// A goal goes in for fixture 2.
r = detectScoreChanges({ 1: "0-0", 2: "1-0" }, [mk(1, 0, 0), mk(2, 2, 0)]);
ok("goal scored → fixture flagged", r.changed.length === 1 && r.changed[0] === 2);
ok("unchanged match not flagged", !r.changed.includes(1));

// New match appearing mid-session is not a 'change'.
r = detectScoreChanges({ 1: "0-0" }, [mk(1, 0, 0), mk(9, 1, 1)]);
ok("newly-seen match not flagged", r.changed.length === 0 && r.next[9] === "1-1");

// Score going from unknown to known is not a flash.
r = detectScoreChanges({ 1: null }, [mk(1, 1, 0)]);
ok("null → known not flagged", r.changed.length === 0);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
