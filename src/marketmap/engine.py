"""role -> MarketMap."""

from datetime import date

from src.marketmap import llm, prompt as prompt_mod
from src.marketmap.parsing import ParseError, extract_json
from src.marketmap.types import MarketMap, Pool


class MapError(RuntimeError):
    """The backend returned something unusable as a map."""


def _pool(d: dict) -> Pool | None:
    name = str(d.get("name") or "").strip()
    logic = str(d.get("transfer_logic") or "").strip()
    if not name or not logic:
        return None

    def strs(key):
        return [str(v).strip() for v in (d.get(key) or []) if str(v).strip()]

    try:
        obv = max(1, min(5, int(d.get("obviousness", 3))))
    except (TypeError, ValueError):
        obv = 3
    try:
        conf = max(0.0, min(1.0, float(d.get("confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5

    return Pool(name=name, transfer_logic=logic, companies=strs("companies"),
                titles=strs("titles"), signals=strs("signals"),
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

    pools = [p for p in (_pool(d) for d in (data.get("pools") or [])
                         if isinstance(d, dict)) if p]
    if not pools:
        raise MapError("no usable pools in response")

    return MarketMap(role_title=role_title, role_text=role_text,
                     core_shape=shape, pools=pools, created=date.today().isoformat())
