// The endpoint resolver, as it ships in the browser.
//
// docs/endpoint.json is written by something outside this repo. For two weeks
// it named a Cloudflare quick tunnel that no longer resolved, so every real
// run died at the fetch and the page said the machine was not always on. The
// machine was awake the whole time, serving the sister app. The published file
// overrode the hardcoded fallback, and the fallback was a dead quick tunnel
// too, so there was nothing to fall back to.
//
// These assertions are what makes "a stale endpoint.json cannot take the app
// down" checkable, rather than a thing we believe.

const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, '..', '..', 'docs', 'app.js');
const src = fs.readFileSync(APP, 'utf8');

const start = src.indexOf('const isEphemeralHost');
const end = src.indexOf('// A saved endpoint normally wins');
if (start < 0 || end < 0) throw new Error('endpoint resolver not found in docs/app.js');

const STABLE = 'https://stable.example.ts.net/model/v1/chat/completions';
let served;
const lift = () => {
  const fetchStub = async () => {
    if (served instanceof Error) throw served;
    if (served === null) return { ok: false };
    return { ok: true, json: async () => served };
  };
  return eval(
    '(function(fetch, Date){' + src.slice(start, end) +
    '; return {hostedURL, isEphemeralHost}; })'
  )(fetchStub, Date);
};

let pass = 0, fail = 0;
function is(actual, expected, label) {
  if (actual === expected) { pass++; return; }
  fail++;
  console.error(`FAIL ${label}\n  expected: ${expected}\n  actual:   ${actual}`);
}

(async () => {
  // The bug, exactly as it happened.
  served = { url: 'https://lift-should-wondering-batch.trycloudflare.com/v1/chat/completions' };
  is(await lift().hostedURL(STABLE), STABLE,
     'a published quick tunnel is ignored in favour of the stable fallback');

  const moved = 'https://elsewhere.example.ts.net/model/v1/chat/completions';
  served = { url: moved };
  is(await lift().hostedURL(STABLE), moved,
     'a stable published address still overrides the constant');

  served = new Error('offline');
  is(await lift().hostedURL(STABLE), STABLE, 'fetch failure falls back');

  served = null;
  is(await lift().hostedURL(STABLE), STABLE, 'a 404 on endpoint.json falls back');

  served = { url: 'http://insecure.example.com/v1/chat/completions' };
  is(await lift().hostedURL(STABLE), STABLE, 'a non-https address is refused');

  const { isEphemeralHost } = lift();
  is(isEphemeralHost('https://a-b-c-d.trycloudflare.com/v1/chat/completions'), true,
     'quick tunnels are recognised');
  is(isEphemeralHost('https://patrick-beastmaster.tailf32530.ts.net/model/v1/chat/completions'), false,
     'the funnel hostname is not ephemeral');

  // What actually ships, right now, in this repo.
  const shipped = JSON.parse(
    fs.readFileSync(path.join(__dirname, '..', '..', 'docs', 'endpoint.json'), 'utf8'));
  is(isEphemeralHost(shipped.url), false, 'the committed endpoint.json is not a quick tunnel');
  const FREE = src.match(/const FREE\s*=\s*\{url:"([^"]+)"/);
  if (!FREE) throw new Error('FREE constant not found in docs/app.js');
  is(isEphemeralHost(FREE[1]), false, 'the hardcoded fallback is not a quick tunnel');
  is(new URL(FREE[1]).origin, new URL(shipped.url).origin,
     'the fallback and endpoint.json point at the same host');

  console.log(`${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
