"use strict";
const $ = s => document.querySelector(s);
const LS = "tmm.settings.v1";

// Points at a bridge fronting a self-hosted Qwen 3.8. No key, no signup,
// nothing for a visitor to configure - which is the entire point. Anyone who
// would rather use their own model changes it in Settings.
const FREE = {url:"https://users-macbook-pro.tailf32530.ts.net/v1/chat/completions",
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
- tells are disqualifiers: what on a profile means this person looks right but is not.
- obviousness: 5 = every recruiter searches here first, 1 = almost nobody would think of it. Rate honestly. Include 1-2 anchor pools and 3-5 non-obvious ones.
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
  const sig=orGroup((p.signals||[]).slice(0,4)); if(sig) parts.push(sig);
  return parts.join(" ");
}
function booleanStr(p){ return [orGroup(p.titles), orGroup(p.companies)].filter(Boolean).join(" AND "); }

async function complete(prompt){
  const s = settings();
  const anthropic = /anthropic\.com/.test(s.url);
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
  const r = await fetch(s.url, {method:"POST", headers, body:JSON.stringify(body)});
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

function poolCard(p, i){
  const el = document.createElement("article"); el.className="pool";
  const obv = Math.max(1, Math.min(5, p.obviousness ?? 3));
  const g = "https://www.google.com/search?q=" + encodeURIComponent(xray(p));
  el.innerHTML = `
    <div class="phead">
      <span class="rank">${String(i+1).padStart(2,"0")}</span>
      <h3></h3>
      <span class="pill ${obv<=2?"rare":""}">obviousness ${obv}/5</span>
    </div>
    <p class="why"></p>
    <div class="rows">
      <div><span class="lbl">Where</span><div class="terms" data-k="companies"></div></div>
      <div><span class="lbl">What they call themselves</span><div class="terms" data-k="titles"></div></div>
      <div><span class="lbl">Look for</span><div class="terms" data-k="signals"></div></div>
      <div><span class="lbl">Rules them out</span><div class="terms out" data-k="tells"></div></div>
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

function renderMap(map, roleTitle){
  const out = $("#out"); out.innerHTML="";
  const shape = document.createElement("div"); shape.className="shape";
  shape.innerHTML = `<span class="lbl">The capability under the title</span><p></p>`;
  shape.querySelector("p").textContent = map.core_shape || "";
  out.appendChild(shape);

  const pools = (map.pools||[]).slice().sort((a,b)=>(a.obviousness??3)-(b.obviousness??3));
  const bar = document.createElement("div"); bar.className="bar";
  bar.innerHTML = `<span>${pools.length} pools for <b></b></span>
    <label class="tog"><input type="checkbox" id="hideobv"> hide the obvious ones</label>`;
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
    renderMap(map, title);
    status(`${map.pools.length} pools.`);
    localStorage.setItem("tmm.last", JSON.stringify({title, map}));
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

window.addEventListener("DOMContentLoaded", ()=>{
  $("#run").onclick = run;
  $("#gear").onclick = openSettings;
  $("#save").onclick = e => {
    e.preventDefault();
    saveSettings({url:$("#url").value.trim(), key:$("#key").value.trim(), model:$("#model").value.trim()});
    $("#settings").close(); status("Endpoint saved. It stays in this browser.");
  };
  document.querySelectorAll("[data-preset]").forEach(b=>b.onclick=e=>{e.preventDefault();applyPreset(b.dataset.preset);});
  const last = localStorage.getItem("tmm.last");
  if(last){ try{ const {title,map}=JSON.parse(last); $("#title").value=title; renderMap(map,title);
    status("Showing your last map."); }catch{} }
  else status("Ready. No key needed \u2014 paste a job description and go.");
});
