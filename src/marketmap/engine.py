"""role -> MarketMap."""

from datetime import date

from src.marketmap import llm, prompt as prompt_mod
from src.marketmap.parsing import ParseError, extract_json
from src.marketmap.obviousness import derive as derive_obviousness
from src.marketmap.searchable import keep as keep_signals
from src.marketmap.types import MarketMap, Pool


class MapError(RuntimeError):
    """The backend returned something unusable as a map."""


def _pool(d: dict, role_title: str = "") -> Pool | None:
    name = str(d.get("name") or "").strip()
    logic = str(d.get("transfer_logic") or "").strip()
    if not name or not logic:
        return None

    def strs(key):
        return [str(v).strip() for v in (d.get(key) or []) if str(v).strip()]

    titles = strs("titles")
    # Derived, not taken from the model. A live playtest caught it scoring
    # quant risk 4/5 for an autonomous-vehicle req and military construction
    # 1/5 for a construction req - wrong in both directions, because it rates
    # its own surprise at unfamiliar vocabulary rather than a recruiter's
    # reach. See obviousness.py.
    obv = derive_obviousness(role_title, titles)
    try:
        conf = max(0.0, min(1.0, float(d.get("confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5

    # A signal that names the pool's own topic back at you is not a search
    # term. Filtered here rather than asked for, because asking did not work.
    signals, dropped = keep_signals(strs("signals"))

    return Pool(name=name, transfer_logic=logic, companies=strs("companies"),
                titles=titles, signals=signals, dropped_signals=dropped,
                tells=strs("tells"), obviousness=obv, confidence=conf)


def generate(role_title: str, role_text: str, *, context=None, complete=None) -> MarketMap:
    complete = complete or llm.complete
    try:
        data = extract_json(complete(
            prompt_mod.build(role_title, role_text, context),
            system=prompt_mod.SYSTEM))
    except ParseError as exc:
        raise MapError(str(exc)) from exc

    shape = str(data.get("core_shape") or "").strip()
    if not shape:
        raise MapError("no core_shape in response")

    pools = [p for p in (_pool(d, role_title) for d in (data.get("pools") or [])
                         if isinstance(d, dict)) if p]
    if not pools:
        raise MapError("no usable pools in response")

    return MarketMap(role_title=role_title, role_text=role_text,
                     core_shape=shape, pools=pools, created=date.today().isoformat())
