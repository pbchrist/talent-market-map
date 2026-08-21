"""talent-market-map: which pools to search, for a role. No database."""

import argparse
import os
import sys

from src.marketmap import graph, store
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
    args = ap.parse_args(argv)

    if args.reuse:
        cached = store.find(args.title)
        if cached:
            print(render(cached, show_all=args.all))
            _graph(cached, args)
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
    return 0


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
