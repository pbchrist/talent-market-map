"""How close is each pool to what the recruiter is already searching?

Answered as a ranking within one map, because that is the only claim the
evidence supports.

The previous version answered it as an absolute 1-5 score and collapsed in
live use: every pool in a payments map scored 1/5, every pool in a pharmacist
map scored 4/5. It was measuring whether the role title's distinctive noun
happened to be a word people put in job titles. "Pharmacist" recurs in every
pharmacy title, so everything looked obvious. "Payments" recurs in none,
because those people call themselves ledger and settlement and billing
engineers, so everything looked exotic. Core banking ledger architects came
back at 1/5 - "almost nobody searches here" - for a payments req.

Two absolute scorers were then tried against every map we have evidence for.
Both fixed the reported failures and both introduced a new false-high, and both
new failures were one phenomenon: a generic process word colliding across
domains. "Model Validation Lead" against "AV validation". "Quality & Compliance
Manager" against "regulatory compliance". The word matches; the sense does not.
No stop list separates senses, and a stop list long enough to try would be the
load-bearing blocklist this codebase refuses elsewhere.

Ordering survived where banding did not - in all four multi-pool maps,
including both that banding got wrong. So this ranks. The reader's actual
question is "which of these do I already know about, so I can hide them",
which is a question about order, and the badge says the score is relative to
this map rather than to the whole market.
"""

import re

# Words that appear in job titles across every industry. Left in, a shared
# "Manager" would make two unrelated pools look like neighbours.
_STOP = {
    "a", "an", "and", "at", "by", "for", "from", "in", "of", "on", "or", "the",
    "to", "with",
    "senior", "staff", "principal", "lead", "head", "chief", "director",
    "manager", "vp", "president", "engineer", "specialist", "analyst",
    "associate", "consultant", "operations", "operation", "services",
    "service", "solutions", "platform", "systems", "system", "group", "team",
    "regional", "district", "area", "global", "national", "developer",
    "architect", "coordinator", "supervisor", "officer", "executive",
    "general", "technician", "administrator", "representative",
    "i", "ii", "iii", "iv", "jr", "sr",
}

# What a pool scores when the map cannot rank it: a single pool has nothing to
# be nearer than, and a map whose pools all tie has no order to report. Saying
# "3" here is saying "no opinion", which is different from saying "average".
UNRANKED = 3

_TOP, _BOTTOM = 5, 1


def _words(text) -> set:
    return {w for w in re.findall(r"[a-z0-9+#]+", str(text or "").lower())
            if w not in _STOP and len(w) > 2}


def closeness(role_title: str, role_text: str, titles) -> float:
    """0.0 to 1.0: how much of what these people call themselves is language
    the recruiter is already steeped in.

    Measured from the title's side. A role carries domain words a genuine
    adjacent pool would never repeat, so scoring from the role's side punishes
    exactly the pools worth finding. And it reads the whole role, not just its
    title: "Staff Engineer, Payments" never says "ledger", but the job
    description does, which is why the title-only version could not see that
    core banking sits next door.
    """
    titles = [t for t in (titles or []) if str(t).strip()]
    if not titles:
        return 0.0
    vocab = _words(role_title) | _words(role_text)
    if not vocab:
        return 0.0

    scores = []
    for t in titles:
        tw = _words(t)
        if tw:
            scores.append(len(vocab & tw) / len(tw))
    # Mean, not max: one generically-named title should not make a whole pool
    # look like home turf.
    return sum(scores) / len(scores) if scores else 0.0


def rank(role_title: str, role_text: str, pool_titles) -> list[int]:
    """Place each pool on a 1-5 scale by its position among the others.

    5 is the closest pool in THIS map, 1 the furthest. Pools that score the
    same share a number, and a map with nothing to separate returns UNRANKED
    throughout rather than inventing an order.
    """
    pools = list(pool_titles or [])
    if len(pools) < 2:
        return [UNRANKED] * len(pools)

    raw = [closeness(role_title, role_text, t) for t in pools]
    tiers = sorted(set(raw), reverse=True)     # distinct scores, closest first
    if len(tiers) == 1:
        return [UNRANKED] * len(pools)

    # Spread the distinct scores evenly over the scale, so the closest pool is
    # always 5 and the furthest always 1 however many tiers there are.
    step = (_TOP - _BOTTOM) / (len(tiers) - 1)
    band = {score: round(_TOP - i * step) for i, score in enumerate(tiers)}
    return [band[r] for r in raw]


__all__ = ["UNRANKED", "closeness", "rank"]
