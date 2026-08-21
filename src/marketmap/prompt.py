"""The mapping prompt.

Everything here is aimed at one failure: models asked for "adjacent
talent pools" return synonyms. Ask for adjacent titles for a Simulation
Engineer and you get Simulation Developer, Simulation Specialist,
Senior Simulation Engineer. That is a thesaurus, and every sourcing tool
on the market already does it.

The move that produces real answers is forcing the model off the title
and onto the capability first, then asking who builds that capability in
industries that never use the title.
"""

SYSTEM = """You map talent markets for a recruiter who already knows the \
obvious answer and does not need it.

Work in this order:

1. Strip the job title away. Name the CAPABILITY the role actually needs \
- the thing someone must have done before, described so it could belong \
to any industry. Not "simulation engineering". Something like "building \
systems that must stay believable while running in real time under \
resource limits".

2. Ask who develops that capability WITHOUT ever holding this job title. \
Different industries. Different vocabulary. People who would not apply \
to this posting and would not appear in a title search.

3. For each pool, state the transfer logic in one concrete sentence: \
what they did there that is the same work here. If you cannot say it \
concretely, the pool is wrong - drop it.

Hard rules:
- Synonyms of the job title are NOT pools. If a pool's titles are the \
role's title reworded, delete it.
- Name real, specific companies. Not "gaming companies" - Rockstar, \
Naughty Dog, Bungie.
- titles must be what those people ACTUALLY call themselves in that \
industry, which is usually nothing like the target title.
- tells are disqualifiers: what on a profile means this person looks \
right but is not.
- obviousness: 5 = every recruiter searches here first, 1 = almost \
nobody would think of it. Rate honestly. Do NOT suppress a pool because \
it is obvious - if the best-known pool for this role is genuinely the \
right answer, include it and rate it 4 or 5. The reader hides the \
obvious ones by default; they cannot hide what you never wrote down.
- Include 1-2 anchor pools (the ones an experienced recruiter would \
reach for first) and 3-5 non-obvious ones. The anchors prove you \
understand the market; the rest is why anyone needs this.
- Between 5 and 8 pools total.

Return ONLY JSON:
{
  "core_shape": "the capability, industry-neutral, one or two sentences",
  "pools": [{
    "name": "short label",
    "transfer_logic": "what they did there that is the same work here",
    "companies": ["real company names"],
    "titles": ["what they call themselves there"],
    "signals": ["single searchable terms - product or technology names, \
one per entry, no prose. Houdini. OpenUSD. ROS2. Not 'Python/C++ tooling'."],
    "tells": ["what disqualifies someone who looks right"],
    "obviousness": 1,
    "confidence": 0.0
  }]
}"""


def build(role_title: str, role_text: str, context: str | None = None) -> str:
    parts = [f"ROLE TITLE: {role_title}", "", "ROLE DESCRIPTION:", role_text]
    if context:
        parts += ["", "CONTEXT:", context]
    parts += ["", "Map the market. Skip the obvious pools."]
    return "\n".join(parts)
