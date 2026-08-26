// Tests for liveUpcoming.js — run: node tests/test_live_upcoming.mjs
import { selectUpcoming, kickoffIn } from "../src/services/liveUpcoming.js";

let pass = 0, fail = 0;
const ok = (n, c) => (c ? (pass++, console.log("  ✓", n)) : (fail++, console.error("  ✗", n)));
const fx = (id, short, ts) => ({ fixture: { id, status: { short }, timestamp: ts } });

// selectUpcoming
const all = [
  fx(1, "1H", 100),     // live
  fx(2, "NS", 300),     // upcoming, later
  fx(3, "FT", 50),      // finished
  fx(4, "NS", 200),     // upcoming, sooner
  fx(5, "NS", 250),     // upcoming, middle
];
const up = selectUpcoming(all, 2);
ok("filters to NS only", up.every((f) => f.fixture.status.short === "NS"));
ok("sorts soonest first", up[0].fixture.id === 4 && up[1].fixture.id === 5);
ok("respects limit", up.length === 2);
ok("empty input → []", selectUpcoming(null).length === 0);

// kickoffIn
const now = 1_000_000_000_000;
const inMs = (mins) => new Date(now + mins * 60000).toISOString();
ok("hours+minutes", kickoffIn(inMs(134), now) === "in 2h 14m");
ok("minutes only", kickoffIn(inMs(8), now) === "in 8m");
ok("sub-minute", kickoffIn(new Date(now + 30000).toISOString(), now) === "in <1m");
ok("past → kicking off", kickoffIn(inMs(-5), now) === "kicking off");
ok("garbage → empty", kickoffIn("not-a-date", now) === "");

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
