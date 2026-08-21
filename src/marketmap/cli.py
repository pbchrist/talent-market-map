"""talent-market-map: which pools to search, for a role. No database."""

import argparse
import os
import sys

from src.marketmap import find as finder, graph, store, web
from src.marketmap.engine import MapError, generate
from src.marketmap.render import render


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="talent-market-map")
    ap.add_argument("--title", required=True, help="the role title")
    ap.add_argument("--role", required=True,
                    help="the job description: a file, or the text itself")
    ap.add_argument("--context", help="stage, location, constraints")
    ap.add_argument("--all", action="store_true", help="include obvious pools")
    ap.add_argument("--reuse", action="store_true",
                    help="load a saved map for this title instead of regenerating")
    ap.add_argument("--graph", nargs="?", const="", metavar="FILE",
                    help="also write an interactive graph. Defaults to "
                         "maps/<slug>.html next to the saved map.")
    ap.add_argument("--open", action="store_true",
                    help="open the graph in your browser once it is written")
    ap.add_argument("--web", nargs="?", const=10, type=int, metavar="N",
                    help="run each pool's X-ray through a search API and return "
                         "the LinkedIn profiles it finds. Needs BRAVE_API_KEY, "
                         "SERPER_API_KEY, or GOOGLE_API_KEY + GOOGLE_CSE_ID.")
    ap.add_argument("--brief", action="store_true",
                    help="for GitHub candidates, read each one's career arc and "
                         "produce an outreach brief. Requires narrative-sourcing "
                         "on the path.")
    ap.add_argument("--find", nargs="?", const=8, type=int, metavar="N",
                    help="search GitHub for people who have actually built "
                         "what each pool is about, and print them with the "
                         "repository that matched. Official API, no scraping.")
    args = ap.parse_args(argv)

    if args.reuse:
        cached = store.find(args.title)
        if cached:
            print(render(cached, show_all=args.all))
            _graph(cached, args)
            _find(cached, args)
            _web(cached, args)
            return 0
        print("no saved map for that title; generating", file=sys.stderr)

    text = open(args.role).read() if os.path.exists(args.role) else args.role
    try:
        m = generate(args.title, text, context=args.context)
    except (MapError, RuntimeError) as exc:
        print(f"map failed: {exc}", file=sys.stderr)
        return 1

    print(render(m, show_all=args.all))
    print(f"\nsaved: {store.save(m)}", file=sys.stderr)
    _graph(m, args)
    _find(m, args)
    _web(m, args)
    return 0


def _web(m, args) -> None:
    """Execute each pool's X-ray. Runs independently of everything else so a
    missing API key costs you nothing but this section."""
    if not args.web:
        return
    backend = web.available()
    print("\n" + "=" * 66)
    print(f"PROFILES FROM THE OPEN WEB  ({backend or 'no backend configured'})")
    print("=" * 66)
    if not backend:
        print("\nSet BRAVE_API_KEY (free, 2k/month at api.search.brave.com),")
        print("SERPER_API_KEY, or GOOGLE_API_KEY + GOOGLE_CSE_ID, then rerun.")
        return
    for pool in (m.pools if args.all else (m.non_obvious or m.pools)):
        try:
            print("\n" + web.render(pool, web.search_pool(pool, limit=args.web)))
        except web.WebError as exc:
            print(f"\n{pool.name}: {exc}")


def _brief(people) -> None:
    """Hand each GitHub candidate to narrative-sourcing for an arc and a brief.

    A soft dependency on purpose: this tool is useful without it, and a
    recruiter who only wants the map should not be made to install a second
    repository to get one.
    """
    try:
        from src.brief import build_brief
        from src.fit import assess
        from src.intake.github import load as load_github
        from src.pipeline import render as render_brief  # noqa: F401
        from src.story import extract_arc
    except ImportError:
        print("\n(--brief needs narrative-sourcing importable; skipping)")
        return
    for c in people:
        try:
            profile = load_github(c.login)
            arc = extract_arc(profile)
            print(f"\n  {c.login}: {arc.throughline}")
            print(f"  open question: {arc.unresolved_tension}")
        except Exception as exc:
            print(f"\n  {c.login}: could not read arc ({exc})")


def _find(m, args) -> None:
    """Search each pool for real people. Runs last so a GitHub outage can
    never cost you the map."""
    if not args.find:
        return
    pools = m.pools if args.all else (m.non_obvious or m.pools)
    print("\n" + "=" * 66)
    print("PEOPLE WHO HAVE BUILT THIS")
    print("=" * 66)
    for pool in pools:
        try:
            people = finder.search_pool(pool, limit=args.find)
        except finder.FindError as exc:
            print(f"\n{pool.name}: search failed - {exc}")
            continue
        print("\n" + finder.render(pool, people))
        if args.brief and people:
            _brief(people[:3])


def _graph(m, args) -> None:
    """Write the interactive graph when asked. Kept separate so a rendering
    problem can never cost you a map that took minutes to generate."""
    if args.graph is None:
        return
    path = args.graph or (store.MAPS_DIR / f"{store.slug(m.role_title)}.html")
    written = graph.write(m, path, show_all=args.all)
    print(f"graph: {written}", file=sys.stderr)
    if args.open:
        import subprocess
        subprocess.run(["open", str(written)], check=False)


if __name__ == "__main__":
    raise SystemExit(main())
