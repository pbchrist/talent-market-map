"""How obvious is this pool, measured rather than asserted.

A live playtest caught the model getting this wrong in both directions on the
same axis. Financial Risk Modeling scored 4/5 for an autonomous-vehicle
simulation req - 5 meaning "every recruiter starts here", which no AV
recruiter does. Military Construction scored 1/5 for a commercial
construction req, when USACE and NAVFAC are adjacent enough that a good
construction recruiter reaches them without help.

The pattern in both errors is the same: the model treats unfamiliar
*vocabulary* as unfamiliar *territory*. It is confidently rating its own
surprise rather than a recruiter's.

Lexical distance from the role's own title is a poor proxy for expert
intuition, and a much better one than a model's guess, because it measures
the thing that actually makes a pool findable: whether the words a recruiter
would already type appear in what these people call themselves. It is also
stable across runs, which the model's number is not.
"""

import re

_STOP = {
    "a","an","and","at","by","for","from","in","of","on","or","the","to","with",
    "senior","staff","principal","lead","head","chief","director","manager",
    "vp","president","engineer","specialist","analyst","associate","consultant",
    "i","ii","iii","iv","jr","sr",
}

UNKNOWN = 3   # no titles offered: neither obvious nor exotic


def _words(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9+#]+", (text or "").lower())
            if w not in _STOP and len(w) > 2}


def derive(role_title: str, titles) -> int:
    """1 (almost nobody searches here) to 5 (everybody starts here).

    Driven by how much of the role's own vocabulary survives into what these
    people call themselves. Generic seniority and function words are stripped
    first, so "Senior Engineer" on both sides proves nothing.
    """
    titles = [t for t in (titles or []) if str(t).strip()]
    if not titles:
        return UNKNOWN

    role = _words(role_title)
    if not role:
        return UNKNOWN

    scores = []
    for t in titles:
        tw = _words(t)
        if not tw:
            continue
        # Measured from the title's side, not the role's. A role title carries
        # domain words a genuine synonym pool would never repeat - "Senior
        # Simulation Engineer, Autonomous Vehicles" against "Simulation
        # Engineer" scores badly from the role's side even though the second
        # is plainly the same job. What matters is the reverse: how much of
        # what these people call themselves is vocabulary the recruiter is
        # already typing.
        scores.append(len(role & tw) / len(tw))

    if not scores:
        return UNKNOWN
    # Mean, not max: one generically-named title should not make a whole pool
    # look obvious. "Construction Engineer" sitting beside "Military
    # Construction Manager" and "Facilities Engineer" describes a pool a
    # recruiter partly reaches, not one they start from.
    best = sum(scores) / len(scores)

    if best >= 0.75:
        return 5
    if best >= 0.45:
        return 4
    if best >= 0.25:
        return 3
    if best > 0:
        return 2
    return 1


__all__ = ["UNKNOWN", "derive"]
