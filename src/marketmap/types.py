"""The map. A Pool is a place people with the right shape actually work,
which is usually not the place the job title points at.
"""

from dataclasses import dataclass, field


@dataclass
class Pool:
    name: str                      # "AAA game engine / procedural generation"
    transfer_logic: str            # why this shape transfers to the role
    companies: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)   # what they call themselves
    signals: list[str] = field(default_factory=list)  # what to look for on a profile
    tells: list[str] = field(default_factory=list)    # what rules them OUT
    obviousness: int = 3           # 1 = nobody searches here, 5 = everybody does
    confidence: float = 0.5
    # Signals the model offered that name a category rather than a thing, so
    # they were pulled out of the search strings. Shown, not hidden: the
    # reader should see what the filter took. See searchable.py.
    dropped_signals: list[str] = field(default_factory=list)


@dataclass
class MarketMap:
    role_title: str
    role_text: str
    core_shape: str                # the capability under the job title
    pools: list[Pool] = field(default_factory=list)
    created: str = ""

    @property
    def non_obvious(self) -> list[Pool]:
        """The pools that justify the tool existing."""
        return sorted([p for p in self.pools if p.obviousness <= 2],
                      key=lambda p: (-p.confidence, p.obviousness))
