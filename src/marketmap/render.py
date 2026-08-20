"""Terminal rendering. Non-obvious pools first, because the obvious ones
are what the recruiter already had before opening this."""

from src.marketmap import strings


def render(m, show_all: bool = False) -> str:
    out = [f"TALENT MARKET MAP — {m.role_title}", f"generated {m.created}", "",
           "THE CAPABILITY UNDER THE TITLE", f"  {m.core_shape}", ""]

    pools = m.pools if show_all else (m.non_obvious or m.pools)
    skipped = len(m.pools) - len(pools)
    out.append(f"{len(pools)} POOL(S)" + (f"  ({skipped} obvious pool(s) hidden — --all to show)" if skipped else ""))
    out.append("")

    for i, p in enumerate(pools, 1):
        out += [f"{'─'*66}", f"{i}. {p.name}",
                f"   obviousness {p.obviousness}/5 · confidence {p.confidence}", "",
                "   WHY IT TRANSFERS", f"   {p.transfer_logic}", ""]
        if p.companies:
            out += ["   WHERE", "   " + ", ".join(p.companies), ""]
        if p.titles:
            out += ["   WHAT THEY CALL THEMSELVES", "   " + ", ".join(p.titles), ""]
        if p.signals:
            out += ["   LOOK FOR", "   " + ", ".join(p.signals), ""]
        if p.tells:
            out += ["   RULES THEM OUT", "   " + ", ".join(p.tells), ""]
        x = strings.xray(p)
        if x:
            out += ["   X-RAY (paste into Google — no seat required)", f"   {x}", ""]
        b = strings.boolean(p)
        if b:
            out += ["   BOOLEAN", f"   {b}", ""]
    out.append("─" * 66)
    out.append("Search these yourself. This tool holds no candidate data.")
    return "\n".join(out)
