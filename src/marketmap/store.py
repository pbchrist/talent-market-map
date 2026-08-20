"""Maps persist. The industry complaint this addresses, verbatim: every
sourcing strategy rebuilds the marketplace understanding from scratch
every time a req opens. A map on disk is the second req starting from
the first one."""

import json
import re
from dataclasses import asdict
from pathlib import Path

from src.marketmap.types import MarketMap, Pool

MAPS_DIR = Path("maps")


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "map"


def save(m: MarketMap, directory: Path = MAPS_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{slug(m.role_title)}.json"
    path.write_text(json.dumps(asdict(m), indent=2))
    return path


def load(path) -> MarketMap:
    d = json.loads(Path(path).read_text())
    pools = [Pool(**p) for p in d.pop("pools", [])]
    return MarketMap(pools=pools, **d)


def find(title: str, directory: Path = MAPS_DIR):
    path = directory / f"{slug(title)}.json"
    return load(path) if path.exists() else None
