"""talent-market-map: which pools to search, for a role. No database."""

import argparse
import os
import sys

from src.marketmap import store
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
    args = ap.parse_args(argv)

    if args.reuse:
        cached = store.find(args.title)
        if cached:
            print(render(cached, show_all=args.all))
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
