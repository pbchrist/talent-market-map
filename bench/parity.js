// Do the JavaScript ports still agree with the Python they were copied from?
//
// The deployed page is what anyone actually judges, and it runs its own copy
// of three gates. Once already, a fix landed in the Python package and never
// reached docs/app.js: the live page kept using the model's obviousness for
// hours while the tests were green. This is the check that would have caught it.
//
//   node bench/parity.js            print this build's answers as JSON
//
// bench/run.py compares them against Python's.
const fs = require("fs");
const src = fs.readFileSync(__dirname + "/../docs/app.js", "utf8");

// Lift the pure functions out of the page script - no DOM, no fetch.
const from = src.indexOf("const OBV_STOP");
const to = src.indexOf("function normalizePool");
const seg = src.slice(from, to);
const api = {};
new Function("exports", seg +
  "\nexports.closeness=closeness;exports.rankPools=rankPools;" +
  "exports.isSearchable=isSearchable;exports.keepSignals=keepSignals;")(api);

const CASES = JSON.parse(fs.readFileSync(__dirname + "/parity-cases.json", "utf8"));
const out = { searchable: {}, rank: {} };
for (const s of CASES.searchable) out.searchable[s] = api.isSearchable(s);
for (const c of CASES.rank) {
  out.rank[c.id] = api.rankPools(c.role_title, c.role_text, c.pools);
}
process.stdout.write(JSON.stringify(out, null, 2) + "\n");
