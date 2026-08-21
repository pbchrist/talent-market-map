"""Is this signal something a recruiter can actually type into a box?

A live playtest returned "Real-Time Digital Audio" as a signal for an
Aerospace Flight Simulation pool. It is the pool's own topic restated. Put
it in a search box and it returns the universe the pool already describes,
so it costs the reader a line and buys them nothing.

The contract has always asked for product and technology names - Houdini,
OpenUSD, ROS2. This enforces it, because asking did not work.

The test leads with name-shape rather than a blocklist, so the blocklist is
not load-bearing. Anything carrying a digit, an internal capital, a symbol
or an acronym is a name and survives no matter what words surround it. Only
a phrase with no name in it at all is judged on its vocabulary, and then
only to reject the case that actually failed: a descriptor with nothing
specific in it.

Erring is asymmetric. A weak signal left in costs a glance; a good one
deleted costs a search the recruiter will never know they could have run.
So the vocabulary list is deliberately short, and words that could plausibly
name a real thing - project, engine, flight - are left out of it.
"""

import re

# Words that describe a category rather than name a thing. Short on purpose:
# every addition is a chance to delete a real term.
CATEGORY = {
    "real", "time", "digital", "analog", "systems", "system", "software",
    "hardware", "engineering", "management", "development", "design",
    "integration", "testing", "modeling", "modelling", "simulation",
    "analysis", "processing", "control", "controls", "tooling", "pipeline",
    "workflow", "automation", "infrastructure", "platform", "framework",
    "technology", "technologies", "solutions", "applications", "services",
    "operations", "tools", "techniques", "methods", "advanced", "modern",
    "based", "general", "and", "or",
}

MAX_WORDS = 3


def _named(token: str) -> bool:
    """A token that could only be a proper name of something."""
    if any(c.isdigit() for c in token):
        return True
    if any(c in "+#." for c in token):
        return True
    for run in re.findall(r"[A-Za-z]+", token):
        # OpenUSD, PyTorch - a capital arriving after a lowercase. Hyphenated
        # Title Case ("Real-Time") splits into separate runs and does not
        # trigger this, which is the point.
        if re.search(r"[a-z][A-Z]", run):
            return True
        if len(run) > 1 and run.isupper():
            return True
    return False


def _parts(token: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", token.lower()) if w]


def is_searchable(signal) -> bool:
    """True when the term names something specific enough to search for."""
    if not isinstance(signal, str):
        return False
    words = signal.split()
    if not words:
        return False
    if len(words) > MAX_WORDS:
        return False
    if any(_named(w) for w in words):
        return True
    # No name anywhere in it. A short phrase can still be a real term a
    # recruiter types ("Project Controls"); a three-word one with nothing
    # specific in it is the failure this module exists for.
    if len(words) >= 3:
        return False
    return not all(p in CATEGORY for w in words for p in _parts(w))


def keep(signals) -> tuple[list[str], list[str]]:
    """Split signals into the ones worth searching and the ones dropped.

    If nothing survives, nothing is dropped. A pool showing three weak terms
    is readable; a pool showing none looks broken and hides the fact that the
    model had something to say.
    """
    signals = [s for s in (signals or []) if isinstance(s, str) and s.strip()]
    kept = [s for s in signals if is_searchable(s)]
    if not kept:
        return signals, []
    return kept, [s for s in signals if s not in kept]


__all__ = ["CATEGORY", "MAX_WORDS", "is_searchable", "keep"]
