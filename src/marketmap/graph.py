"""MarketMap -> a self-contained interactive graph.

The map is a spatial argument, so it deserves a spatial rendering: the role
at the centre, pools placed at a radius set by how few recruiters search
there, employers orbiting their pool. Reading the terminal output tells you
the same facts; seeing it tells you the shape.

The page carries no dependencies. 3D projection, depth sorting and hit
testing are a hundred lines of canvas work, which is cheaper than shipping
a rendering engine and means the file opens instantly from disk with no
network at all. That matters: these get emailed to hiring managers.
"""

import html
import json
from pathlib import Path

from src.marketmap import strings
from src.marketmap.types import MarketMap

TEMPLATE = Path(__file__).parent / "templates" / "graph.html"

# Long pool names are wrapped for the node label so they do not run across
# their neighbours. Two lines is the most a label can carry and stay legible.
_WRAP_AT = 22


def _wrap(name: str) -> str:
    words, lines, cur = name.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > _WRAP_AT:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines[:2]) if len(lines) > 1 else name


def _pool_payload(pool) -> dict:
    return {
        "n": _wrap(pool.name),
        "o": pool.obviousness,
        "c": pool.confidence,
        "why": pool.transfer_logic,
        "co": pool.companies,
        "ti": pool.titles,
        "sg": pool.signals,
        "tl": pool.tells,
        "x": strings.xray(pool),
    }


def render(m: MarketMap, show_all: bool = False) -> str:
    """Return the complete HTML for a map. No external requests, no build."""
    pools = m.pools if show_all else (m.non_obvious or m.pools)
    data = (
        "const POOLS = " + json.dumps([_pool_payload(p) for p in pools], indent=1) + ";\n"
        "const ROLE_SHAPE = " + json.dumps(m.core_shape) + ";\n"
        "const ROLE_TITLE = " + json.dumps(m.role_title) + ";\n"
    )
    page = TEMPLATE.read_text(encoding="utf-8")
    return (page
            .replace("/*__MAP_DATA__*/", data)
            .replace("__TITLE__", html.escape(m.role_title))
            .replace("__ROLE__", html.escape(m.role_title))
            .replace("__POOLCOUNT__", str(len(pools))))


def write(m: MarketMap, path, show_all: bool = False) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(m, show_all=show_all), encoding="utf-8")
    return path


__all__ = ["render", "write"]
