# src/qbbn/cli/commands/show.py
"""
Show all stages for an example.
"""

import redis

from qbbn.core.pipeline import Pipeline


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "show",
        help="Show all stages for an example."
    )
    parser.add_argument("example_id", help="The example UUID.")
    parser.add_argument("--db", type=int, default=0)
    parser.set_defaults(func=run)


def run(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    pipeline = Pipeline(client)
    
    data = pipeline.show(args.example_id)
    
    if data["raw"] is None:
        print(f"Example {args.example_id} not found")
        return
    
    print(f"ID:  {data['id']}")
    print(f"Raw: {data['raw']}")
    
    if data["tokens"]:
        print("\nTokens:")
        for t in data["tokens"]:
            print(f"  {t.position:3d}: {t.text}")
    
    if data["corrected"]:
        print("\nCorrected:")
        for c in data["corrected"]:
            if c.original != c.corrected:
                print(f"  {c.original} → {c.corrected}")
            else:
                print(f"  {c.corrected}")