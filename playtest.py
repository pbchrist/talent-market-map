import json, re, urllib.request, time

ENDPOINT='https://song-pattern-rice-graham.trycloudflare.com/v1/chat/completions'

def call(system,prompt,label):
    print('\n'+'='*80+'\n'+label+'\n'+'='*80)
    body=json.dumps({'messages':[{'role':'system','content':system},{'role':'user','content':prompt}],'temperature':0.2,'max_tokens':8000}).encode()
    req=urllib.request.Request(ENDPOINT,data=body,headers={'Content-Type':'application/json'},method='POST')
    t=time.time()
    try:
        with urllib.request.urlopen(req,timeout=300) as r: raw=r.read().decode()
    except Exception as e:
        print('LIVE CALL FAILED',repr(e)); return None
    print(f'elapsed={time.time()-t:.1f}s')
    d=json.loads(raw); m=d.get('choices',[{}])[0].get('message',{})
    text=re.sub(r'<think>[\s\S]*?</think>','',m.get('content') or '',flags=re.I).strip()
    print(text)
    return text

TMM='''You map talent markets for a recruiter who already knows the obvious answer and does not need it.
Work in this order:
1. Strip the job title away. Name the CAPABILITY the role actually needs - the thing someone must have done before, described so it could belong to any industry.
2. Ask who develops that capability WITHOUT ever holding this job title. Different industries. Different vocabulary. People who would not apply to this posting and would not appear in a title search.
3. For each pool, state the transfer logic in one concrete sentence: what they did there that is the same work here. If you cannot say it concretely, drop the pool.
Hard rules:
- Synonyms of the job title are NOT pools.
- Name real, specific companies.
- titles must be what those people ACTUALLY call themselves in that industry.
- tells are disqualifiers.
- obviousness: 5 = every recruiter searches here first, 1 = almost nobody would think of it. Include 1-2 anchor pools and 3-5 non-obvious ones.
- signals must be single searchable terms, product or technology names, one per entry, no prose.
- Between 5 and 8 pools.
Return ONLY JSON:
{"core_shape":"the capability, industry-neutral","pools":[{"name":"short label","transfer_logic":"what they did there that is the same work here","companies":["real names"],"titles":["what they call themselves there"],"signals":["searchable terms"],"tells":["what disqualifies someone who looks right"],"obviousness":1,"confidence":0.0}]}'''

cases=[
('TMM GPU THERMAL','Principal Engineer, GPU Data Center Thermal Reliability','''We operate multi-megawatt GPU clusters used for AI training. Own reliability of the thermal and power-control envelope across liquid-cooled racks. Design failure detection, automated containment, and recovery for pump failures, coolant leaks, heat excursions, power transients, and cascading rack faults. Partner with facilities and firmware teams, build instrumentation and simulation for failure modes, and make architecture decisions that prevent a localized fault from taking down an entire training fabric. Need deep experience with mission-critical systems, controls, telemetry, fault isolation, and high-availability operations.'''),
('TMM CLINICAL CAPACITY','Director, Clinical Capacity Operations','''Own real-time capacity across a regional hospital system: bed availability, staffing constraints, transfers, emergency department boarding, elective surgery demand, and surge response. Build operating mechanisms and tooling that turn incomplete, rapidly changing information into allocation decisions across multiple hospitals. Lead teams that coordinate clinicians, transport, command centers and executives during normal operations and crises. Need someone who has run high-stakes constrained-resource networks, not just built dashboards.'''),
('TMM AI RED TEAM','AI Red Team Program Lead','''Build and run adversarial evaluation for foundation models before release. Design realistic attack scenarios, coordinate specialists who probe model behavior, convert findings into repeatable test suites, prioritize ambiguous risk, and brief engineering and policy leaders on release decisions. Need someone who can create adversarial exercises, distinguish theoretical risk from operational failure, and build a program that gets more rigorous after every incident.''')]
for label,title,role in cases:
    call(TMM,f'ROLE TITLE: {title}\n\nROLE DESCRIPTION:\n{role}\n\nMap the market. Skip the obvious pools.',label)

NS='''You read a person's career history and identify the story in it: not a summary of what they did, but the arc underneath it.
You are looking for:
- the throughline: the one thing that stays constant across every move
- departures: what they moved away from, and what that suggests
- pursuits: what they were visibly reaching toward
- the unresolved tension: the open question their next move would answer
Hard rules:
1. Every departure and pursuit must quote VERBATIM text from the profile as its evidence. Copy the characters exactly. Do not paraphrase or tidy the quote. A quote that does not appear word for word will be discarded automatically.
2. If you cannot find verbatim text supporting a claim, omit the claim. An honest short arc beats a well-written invented one.
3. You are inferring about a real person from partial evidence. Prefer the plainer reading.
Return ONLY JSON:
{"throughline":"one sentence","unresolved_tension":"one sentence","departures":[{"description":"...","evidence":"verbatim quote","confidence":0.0}],"pursuits":[{"description":"...","evidence":"verbatim quote","confidence":0.0}]}
confidence is 0-1 and should reflect genuine doubt.'''

profiles=[
('NS DENSE',"""About
I have spent eleven years in payments and I still find settlement interesting, which I'm told is a warning sign.

Experience
Payments Engineer, Nordvik Bank — 2013-2017
Worked on the core ledger. Learned that the interesting problems in payments are all reconciliation problems wearing a costume.

Senior Engineer, Tessellate (Series A fintech) — 2017-2020
Employee 12. Built the settlement engine that we later found out was the only reason our biggest customer stayed. Left when we were acquired and the roadmap became someone else's.

Staff Engineer, Bandolier — 2020-2023
Rebuilt their reconciliation pipeline. Good work, wrong company. The engineering was fine and the business kept changing its mind about what it was.

Principal Engineer, Kestrel Payments — 2023-present
Doing the same thing at a bigger scale. Increasingly interested in the fraud side, which I have no formal background in."""),
('NS SPARSE',"""Engineer, Trellis — 2018-2020
Junior Engineer.

Engineer, Halverson Group — 2020-2022
Worked on internal tools.

Engineer, Solace — 2022-present
Building things."""),
('NS PIVOT',"""I started as a litigation associate because I liked difficult problems and being in the room when decisions mattered. After four years I realized I was spending more time explaining technical evidence to lawyers than practicing law.

Litigation Associate, Mercer Hale — 2014-2018
Handled complex commercial disputes and became the person partners called when a case turned on software, data, or an expert witness.

Product Counsel, Northline Security — 2018-2021
Moved in-house because I wanted to work with builders before problems became lawsuits. Partnered with security engineering on incident response, disclosure, and product launches.

Director, Trust & Safety, CurrentCo — 2021-present
Built the investigations and escalation function from scratch. The work I like most is still the boundary between a messy technical fact pattern and a decision somebody has to own. I miss being close to the product and have no interest in becoming a general-purpose legal executive.""")]

def norm(t): return re.sub(r'\s+',' ',str(t or '').replace('‘',"'").replace('’',"'").replace('“','"').replace('”','"')).strip()
def canon(t):
    t=norm(t); t=re.sub(r'^(\.\.\.|…)+|(\.\.\.|…)+$','',t); t=re.sub(r'^[\s"\'.,;:\-—–]+|[\s"\'.,;:\-—–]+$','',t); return t.lower()
def verify(ev,raw):
    n=canon(ev); return len(n)>=12 and n in norm(raw).lower()
def obj(text):
    if not text:return None
    i=text.find('{');
    if i<0:return None
    d=0;q=False;e=False
    for j in range(i,len(text)):
        c=text[j]
        if q:
            if e:e=False
            elif c=='\\':e=True
            elif c=='"':q=False
            continue
        if c=='"':q=True
        elif c=='{':d+=1
        elif c=='}':
            d-=1
            if d==0:return json.loads(text[i:j+1])

for label,raw in profiles:
    text=call(NS,f'PROFILE TEXT (quote only from between these markers):\n---BEGIN PROFILE---\n{raw}\n---END PROFILE---',label)
    try:data=obj(text)
    except Exception as e: print('PARSE FAIL',e); continue
    if not data:continue
    beats=(data.get('departures') or [])+(data.get('pursuits') or [])
    kept=[b for b in beats if isinstance(b,dict) and verify(b.get('evidence',''),raw)]
    print(f'VERIFIER proposed={len(beats)} kept={len(kept)} dropped={len(beats)-len(kept)}')
    for b in beats: print(('KEEP' if b in kept else 'DROP'),b.get('description'),'|',repr(b.get('evidence')))

print('\nPLAYTEST COMPLETE')
