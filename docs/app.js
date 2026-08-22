"use strict";
const $ = s => document.querySelector(s);
const LS = "tmm.settings.v1";

// Points at a bridge fronting a self-hosted Qwen 3.8. No key, no signup,
// nothing for a visitor to configure - which is the entire point. Anyone who
// would rather use their own model changes it in Settings.
// Deliberately NOT the tailnet hostname. Anyone on the same tailnet resolves
// that to a 100.x address and Chrome blocks a public page from reaching a
// private one, so the app worked for strangers and failed for its owner.
// This resolves to Cloudflare for everybody.
const FREE = {url:"https://song-pattern-rice-graham.trycloudflare.com/v1/chat/completions",
              model:"", key:""};

const PRESETS = {
  hosted:    {url:FREE.url, model:FREE.model, key:false},
  openai:    {url:"https://api.openai.com/v1/chat/completions", model:"gpt-4o", key:true},
  anthropic: {url:"https://api.anthropic.com/v1/messages",      model:"claude-sonnet-4-5", key:true},
  local:     {url:"http://localhost:8080/v1/chat/completions",  model:"", key:false},
};

const SYSTEM = `You map talent markets for a recruiter who already knows the obvious answer and does not need it.

Work in this order:

1. Strip the job title away. Name the CAPABILITY the role actually needs - the thing someone must have done before, described so it could belong to any industry.

2. Ask who develops that capability WITHOUT ever holding this job title. Different industries. Different vocabulary. People who would not apply to this posting and would not appear in a title search.

3. For each pool, state the transfer logic in one concrete sentence: what they did there that is the same work here. If you cannot say it concretely, drop the pool.

Hard rules:
- Synonyms of the job title are NOT pools. If a pool's titles are the role's title reworded, delete it.
- Name real, specific companies.
- titles must be what those people ACTUALLY call themselves in that industry.
- titles must name the people who DID THE WORK in transfer_logic, not the industry's common job titles. Naming the setting instead of the function is the most damaging error here, because the search string is built from these. For a theme-park pool on a capital-projects role, "Attraction Manager" and "Maintenance Supervisor" are the setting - they run the park. "Project Controls Manager", "Commissioning Manager" and "Owner's Representative" are the function - they built it. Avoid junior catch-alls like "Project Coordinator" that exist in every industry and select for nobody.
- tells are disqualifiers: what on a profile means this person looks right but is not.
- obviousness: your number is recomputed from the titles before the reader sees it; what matters here is WHICH pools you write down. Include 1-2 anchor pools (the obvious ones, to prove you know the market) and 3-5 non-obvious ones.
- signals must be single searchable terms - product or technology names, one per entry, no prose.
- Between 5 and 8 pools.

Return ONLY JSON:
{"core_shape":"the capability, industry-neutral","pools":[{"name":"short label","transfer_logic":"what they did there that is the same work here","companies":["real names"],"titles":["what they call themselves there"],"signals":["searchable terms"],"tells":["what disqualifies someone who looks right"],"obviousness":1,"confidence":0.0}]}`;

function settings(){
  let s = {};
  try { s = JSON.parse(localStorage.getItem(LS)) || {}; } catch {}
  // Works with nothing configured. Anyone who wants their own model can
  // point it somewhere else in Settings; nobody has to.
  if(!s.url) s = {...FREE};
  return s;
}
function saveSettings(s){ localStorage.setItem(LS, JSON.stringify(s)); }

function quote(t){ t=String(t).trim().replace(/^"|"$/g,""); return /\s/.test(t) ? `"${t}"` : t; }
function orGroup(a){ const c=[...new Set((a||[]).filter(x=>x&&x.trim()))].map(quote);
  return c.length>1 ? "("+c.join(" OR ")+")" : (c[0]||""); }
function xray(p, site="linkedin.com/in"){
  const parts=[`site:${site}`];
  [orGroup(p.titles), orGroup(p.companies)].forEach(g=>{ if(g) parts.push(g); });
  // Filtered again here: keepSignals lets prose through when a pool has
  // nothing better so the reader can see it, but it must never reach a
  // search string.
  const sig=orGroup((p.signals||[]).filter(isSearchable).slice(0,4));
  if(sig) parts.push(sig);
  return parts.join(" ");
}
function booleanStr(p){ return [orGroup(p.titles), orGroup(p.companies)].filter(Boolean).join(" AND "); }

// ---- where the hosted model actually is -------------------------------------
// The public address is a Cloudflare quick tunnel, and a quick tunnel gets a
// brand-new random hostname every time cloudflared restarts. The server
// publishes wherever it currently is to endpoint.json beside this file, and a
// timer keeps that current. The constant above is only the fallback for when
// that file is missing.
let RESOLVED_URL = null;
async function hostedURL(fallback){
  if(RESOLVED_URL) return RESOLVED_URL;
  try{
    const r = await fetch("endpoint.json?t=" + Date.now(), {cache:"no-store"});
    if(r.ok){
      const d = await r.json();
      if(d && typeof d.url === "string" && /^https:\/\//.test(d.url)){
        return (RESOLVED_URL = d.url);
      }
    }
  }catch(e){ /* offline, or the file is not there yet - use the fallback */ }
  return (RESOLVED_URL = fallback);
}

// A saved endpoint normally wins: someone chose it in Settings. The exception
// is a saved tunnel address, which was never a choice - just a snapshot of
// where the tunnel happened to be that day. Left alone it would pin whoever
// saved one to a dead host forever, which breaks the app worst for the people
// who opened Settings most.
async function endpointFor(s, fallback){
  if(s.url && !/\.trycloudflare\.com/.test(s.url)) return s.url;
  return await hostedURL(fallback);
}

async function complete(prompt){
  const s = settings();
  const url = await endpointFor(s, FREE.url);
  const anthropic = /anthropic\.com/.test(url);
  const headers = {"Content-Type":"application/json"};
  let body;
  if(anthropic){
    headers["x-api-key"] = s.key || "";
    headers["anthropic-version"] = "2023-06-01";
    headers["anthropic-dangerous-direct-browser-access"] = "true";
    body = {model:s.model||"claude-sonnet-4-5", max_tokens:4000, system:SYSTEM,
            messages:[{role:"user",content:prompt}]};
  } else {
    if(s.key) headers["Authorization"] = "Bearer " + s.key;
    body = {messages:[{role:"system",content:SYSTEM},{role:"user",content:prompt}],
            temperature:0.2, max_tokens:8000};
    if(s.model) body.model = s.model;
  }
  const r = await fetch(url, {method:"POST", headers, body:JSON.stringify(body)});
  if(!r.ok){
    const t = await r.text();
    throw new Error(`${r.status} from your endpoint. ${t.slice(0,200)}`);
  }
  const d = await r.json();
  if(anthropic) return (d.content||[]).map(c=>c.text||"").join("");
  const m = d.choices?.[0]?.message || {};
  const text = (m.content||"").replace(/<think>[\s\S]*?<\/think>/gi,"").trim();
  if(!text && m.reasoning_content) throw new Error("Model returned reasoning but no answer — raise its token limit.");
  return text;
}

function extractJSON(text){
  const i = text.indexOf("{"); if(i<0) throw new Error("The model did not return JSON.");
  let depth=0, inStr=false, esc=false;
  for(let j=i;j<text.length;j++){
    const c=text[j];
    if(inStr){ if(esc) esc=false; else if(c==="\\") esc=true; else if(c==='"') inStr=false; continue; }
    if(c==='"') inStr=true;
    else if(c==="{") depth++;
    else if(c==="}"){ depth--; if(!depth) return JSON.parse(text.slice(i,j+1)); }
  }
  throw new Error("The model's JSON was cut off — raise its token limit.");
}

// --- Derived, never believed --------------------------------------------
// Both of these used to be taken from the model and both were wrong in live
// use. The Python package has the same two functions with the same tests;
// this is the port, and it must stay in step. See src/marketmap/obviousness.py
// and src/marketmap/searchable.py for the reasoning.

const OBV_STOP = new Set(["a","an","and","at","by","for","from","in","of","on",
  "or","the","to","with","senior","staff","principal","lead","head","chief",
  "director","manager","vp","president","engineer","specialist","analyst",
  "associate","consultant","operations","operation","services","service",
  "solutions","platform","systems","system","group","team","regional",
  "district","area","global","national","developer","architect","coordinator",
  "supervisor","officer","executive","general","technician","administrator",
  "representative","i","ii","iii","iv","jr","sr"]);

const UNRANKED = 3;   // "no opinion" - not "average"

function obvWords(text){
  return new Set((String(text||"").toLowerCase().match(/[a-z0-9+#]+/g)||[])
    .filter(w => !OBV_STOP.has(w) && w.length > 2));
}

// 0..1: how much of what these people call themselves is language the
// recruiter is already steeped in. Reads the whole role, not just the title -
// "Staff Engineer, Payments" never says "ledger", but the job description
// does, and that is why the title-only version could not see that core
// banking sits next door.
function closeness(roleTitle, roleText, titles){
  const list = (titles||[]).filter(x => x && String(x).trim());
  if(!list.length) return 0;
  const vocab = new Set([...obvWords(roleTitle), ...obvWords(roleText)]);
  if(!vocab.size) return 0;
  const scores = [];
  for(const t of list){
    const tw = obvWords(t);
    if(!tw.size) continue;
    let hit = 0; tw.forEach(w => { if(vocab.has(w)) hit++; });
    scores.push(hit / tw.size);
  }
  if(!scores.length) return 0;
  // Mean, not max: one generically-named title should not make a whole pool
  // look like home turf.
  return scores.reduce((a,b)=>a+b,0) / scores.length;
}

// 5 = closest pool in THIS map, 1 = furthest. Ranked rather than scored,
// because an absolute number shipped once and came back all-1 on a payments
// map and all-4 on a pharmacist map. Ties share a number; a map with nothing
// to separate returns UNRANKED throughout rather than inventing an order.
function rankPools(roleTitle, roleText, poolTitles){
  const pools = poolTitles || [];
  if(pools.length < 2) return pools.map(()=>UNRANKED);
  const raw = pools.map(t => closeness(roleTitle, roleText, t));
  const tiers = [...new Set(raw)].sort((a,b)=>b-a);
  if(tiers.length === 1) return pools.map(()=>UNRANKED);
  const step = 4 / (tiers.length - 1);
  const band = new Map(tiers.map((s,i)=>[s, Math.round(5 - i*step)]));
  return raw.map(r => band.get(r));
}

const SIG_CATEGORY = new Set(["real","time","digital","analog","systems",
  "system","software","hardware","engineering","management","development",
  "design","integration","testing","modeling","modelling","simulation",
  "analysis","processing","control","controls","tooling","pipeline",
  "workflow","automation","infrastructure","platform","framework",
  "technology","technologies","solutions","applications","services",
  "operations","tools","techniques","methods","advanced","modern","based",
  "general","and","or"]);

// A token that could only be the proper name of something.
function sigNamed(token){
  if(/\d/.test(token)) return true;
  if(/[+#.]/.test(token)) return true;
  for(const run of (token.match(/[A-Za-z]+/g)||[])){
    if(/[a-z][A-Z]/.test(run)) return true;          // OpenUSD, PyTorch
    if(run.length > 1 && run === run.toUpperCase()) return true;  // ARINC
  }
  return false;
}

function isSearchable(signal){
  if(typeof signal !== "string") return false;
  const words = signal.split(/\s+/).filter(Boolean);
  if(!words.length || words.length > 3) return false;
  if(words.some(sigNamed)) return true;
  if(words.length >= 3) return false;
  return !words.every(w => (w.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean))
    .every(part => SIG_CATEGORY.has(part)));
}

// Never empties a pool: a pool showing weak terms is readable, one showing
// none looks broken.
function keepSignals(signals){
  const all = (signals||[]).filter(s => typeof s === "string" && s.trim());
  const kept = all.filter(isSearchable);
  if(!kept.length) return {kept: all, dropped: []};
  return {kept, dropped: all.filter(s => !kept.includes(s))};
}

function normalizePool(p){
  const {kept, dropped} = keepSignals(p.signals);
  return Object.assign({}, p, {signals: kept, dropped_signals: dropped});
}

// What the badge says. The number is a position among these pools, so the
// label must not imply a universal scale.
function nearLabel(n, ranked){
  if(!ranked) return "not ranked";
  if(n === 5) return "closest in this map";
  if(n === 1) return "furthest in this map";
  return `${n}/5 near your search`;
}

function poolCard(p, i){
  const el = document.createElement("article"); el.className="pool";
  const obv = p.obviousness ?? 3;   // derived in normalizePool, not the model's number
  const g = "https://www.google.com/search?q=" + encodeURIComponent(xray(p));
  el.innerHTML = `
    <div class="phead">
      <span class="rank">${String(i+1).padStart(2,"0")}</span>
      <h3></h3>
      <span class="pill ${obv<=2?"rare":""}">${nearLabel(obv, p._ranked)}</span>
    </div>
    <p class="why"></p>
    <div class="rows">
      <div><span class="lbl">Where</span><div class="terms" data-k="companies"></div></div>
      <div><span class="lbl">What they call themselves</span><div class="terms" data-k="titles"></div></div>
      <div><span class="lbl">Look for</span><div class="terms" data-k="signals"></div></div>
      <div><span class="lbl">Rules them out</span><div class="terms out" data-k="tells"></div></div>
      <div><span class="lbl">Not searchable, so not used</span><div class="terms cut" data-k="dropped_signals"></div></div>
    </div>
    <div class="strings">
      <span class="lbl">Search this pool</span>
      <pre></pre>
      <div class="btns">
        <a class="btn go" target="_blank" rel="noopener">Run this search</a>
        <button class="btn copy" type="button">Copy X-ray</button>
        <button class="btn copyb" type="button">Copy Boolean</button>
      </div>
    </div>`;
  el.querySelector("h3").textContent = p.name || "";
  el.querySelector(".why").textContent = p.transfer_logic || "";
  el.querySelectorAll(".terms").forEach(box=>{
    (p[box.dataset.k]||[]).forEach(t=>{
      const s=document.createElement("span"); s.className="term"; s.textContent=t; box.appendChild(s);
    });
    if(!box.children.length) box.closest("div").style.display="none";
  });
  el.querySelector("pre").textContent = xray(p);
  el.querySelector(".go").href = g;
  el.querySelector(".copy").onclick = e => copy(e.target, xray(p));
  el.querySelector(".copyb").onclick = e => copy(e.target, booleanStr(p));
  return el;
}

function copy(btn, text){
  const done=()=>{ const o=btn.textContent; btn.textContent="Copied"; setTimeout(()=>btn.textContent=o,1400); };
  if(navigator.clipboard) navigator.clipboard.writeText(text).then(done, done); else done();
}

function renderMap(map, roleTitle, roleText){
  const out = $("#out"); out.innerHTML="";
  const shape = document.createElement("div"); shape.className="shape";
  shape.innerHTML = `<span class="lbl">The capability under the title</span><p></p>`;
  shape.querySelector("p").textContent = map.core_shape || "";
  out.appendChild(shape);

  const pools = (map.pools||[]).map(normalizePool);
  const ranks = rankPools(roleTitle, roleText || "", pools.map(p => p.titles));
  const ranked = new Set(ranks).size > 1;
  pools.forEach((p,i) => { p.obviousness = ranks[i]; p._ranked = ranked; });
  pools.sort((a,b)=>(a.obviousness??3)-(b.obviousness??3));
  map.pools = pools;   // so the status line and storage see what was rendered
  const bar = document.createElement("div"); bar.className="bar";
  bar.innerHTML = `<span>${pools.length} pools for <b></b></span>
    <label class="tog"><input type="checkbox" id="hideobv"> hide the closest ones</label>
    <span class="legend">ranked against the other pools in this map, not the whole market</span>`;
  bar.querySelector("b").textContent = roleTitle;
  out.appendChild(bar);

  const list = document.createElement("div"); list.className="pools";
  pools.forEach((p,i)=>list.appendChild(poolCard(p,i)));
  out.appendChild(list);

  $("#hideobv").onchange = e => {
    list.querySelectorAll(".pool").forEach((el,i)=>{
      el.style.display = (e.target.checked && (pools[i].obviousness??3) > 2) ? "none" : "";
    });
  };
}

async function run(){
  const title = $("#title").value.trim();
  const role  = $("#role").value.trim();
  if(!title || role.length < 30){ status("Give it a title and a real job description.", true); return; }
  $("#run").disabled = true;
  status("Reading the role. This takes as long as your model takes.");
  try{
    const prompt = `ROLE TITLE: ${title}\n\nROLE DESCRIPTION:\n${role}\n\nMap the market. Skip the obvious pools.`;
    const map = extractJSON(await complete(prompt));
    if(!map.pools?.length) throw new Error("No usable pools came back. Try a longer description.");
    renderMap(map, title, role);
    const cut = map.pools.reduce((n,p)=>n+(p.dropped_signals||[]).length, 0);
    status(`${map.pools.length} pools.` + (cut
      ? ` ${cut} signal${cut>1?"s":""} named a category rather than a search term and were left out of the strings.`
      : ""));
    remember(title, {title, role, map});
  }catch(e){ status(e.message, true); }
  finally{ $("#run").disabled = false; }
}

function status(msg, bad){ const s=$("#status"); s.textContent=msg; s.className = bad?"bad":""; }

function openSettings(){
  const s = settings();
  $("#url").value = s.url || ""; $("#key").value = s.key || ""; $("#model").value = s.model || "";
  $("#settings").showModal();
}
function applyPreset(name){
  const p = PRESETS[name]; if(!p) return;
  $("#url").value = p.url; $("#model").value = p.model;
  if(!p.key) $("#key").value = "";
}

const HKEY = "tmm.history";

// ---- kinematic feel ---------------------------------------------------------
// A synthesized click rather than an audio file: nothing to load, nothing for
// the CSP to block, and it stays in step with the press animation. Two
// transients ~12ms apart read as a switch closing; one alone reads as a beep.
let AC = null;
let SOUND = localStorage.getItem("ui.sound") !== "off";
const QUIET = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function tick(){
  if(!SOUND || QUIET()) return;
  try{
    AC = AC || new (window.AudioContext || window.webkitAudioContext)();
    if(AC.state === "suspended") AC.resume();
    const t = AC.currentTime;
    for(const [at, freq, gain] of [[0, 1850, 0.055], [0.012, 1120, 0.03]]){
      const o = AC.createOscillator(), g = AC.createGain();
      o.type = "square";
      o.frequency.setValueAtTime(freq, t + at);
      g.gain.setValueAtTime(gain, t + at);
      g.gain.exponentialRampToValueAtTime(0.0001, t + at + 0.028);
      o.connect(g); g.connect(AC.destination);
      o.start(t + at); o.stop(t + at + 0.035);
    }
  }catch(e){ /* no audio on this device - the press animation still lands */ }
}

// ---- prior searches ---------------------------------------------------------
// Kept OUT of the input boxes on purpose. Restoring the last run into the form
// meant every new search started by deleting someone else's text.
const HMAX = 8;
function hist(){ try{ return JSON.parse(localStorage.getItem(HKEY)) || []; }catch{ return []; } }
function remember(label, payload){
  const h = hist().filter(e => e.label !== label);
  h.unshift({label, when: Date.now(), payload});
  try{ localStorage.setItem(HKEY, JSON.stringify(h.slice(0, HMAX))); }
  catch(e){ /* quota - drop the oldest and try once */
    try{ localStorage.setItem(HKEY, JSON.stringify(h.slice(0, 3))); }catch(e2){}
  }
  drawRecent();
}
function drawRecent(){
  const box = document.getElementById("recent"); if(!box) return;
  const h = hist();
  box.innerHTML = "";
  box.hidden = !h.length;
  if(!h.length) return;
  const lbl = document.createElement("span");
  lbl.className = "rlbl"; lbl.textContent = "Prior searches";
  box.appendChild(lbl);
  h.forEach(e => {
    const c = document.createElement("button");
    c.type = "button"; c.className = "chip";
    c.textContent = e.label.length > 46 ? e.label.slice(0, 44) + "…" : e.label;
    c.title = "Show this again — your boxes stay as they are";
    c.onclick = () => replay(e);
    box.appendChild(c);
  });
  const clr = document.createElement("button");
  clr.type = "button"; clr.className = "chip clear"; clr.textContent = "Clear";
  clr.onclick = () => { localStorage.removeItem(HKEY); drawRecent();
                        status("Prior searches cleared."); };
  box.appendChild(clr);
}

// One handler for the whole page, so anything button-shaped clicks.
document.addEventListener("pointerdown", e => {
  if(e.target.closest("button, .chip")) tick();
}, true);

function replay(e){
  // Renders only. The input boxes are never written to.
  renderMap(e.payload.map, e.payload.title, e.payload.role || "");
  status("Showing a prior map. The boxes above are still yours.");
}

window.addEventListener("DOMContentLoaded", ()=>{
  $("#run").onclick = run;
  $("#gear").onclick = openSettings;
  $("#save").onclick = e => {
    e.preventDefault();
    saveSettings({url:$("#url").value.trim(), key:$("#key").value.trim(), model:$("#model").value.trim()});
    $("#settings").close(); status("Endpoint saved. It stays in this browser.");
  };
  document.querySelectorAll("[data-preset]").forEach(b=>b.onclick=e=>{e.preventDefault();applyPreset(b.dataset.preset);});
  // Deliberately does NOT refill the form. The prior run is a chip you can
  // click, not text you have to delete before you can type your own.
  drawRecent();
  status("Ready. No key needed \u2014 paste a job description and go.");
});
