# src/qbbn/cli/commands/correct.py
"""
Spell correct an example by UUID.
"""

import redis

from qbbn.core.pipeline import Pipeline


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "correct",
        help="Spell correct an example (requires tokenize first)."
    )
    parser.add_argument("example_id", help="The example UUID.")
    parser.add_argument("--db", type=int, default=0)
    parser.set_defaults(func=run)


def run(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    pipeline = Pipeline(client)
    
    corrected = pipeline.run_correct(args.example_id)
    
    for c in corrected:
        if c.original != c.corrected:
            print(f"{c.original} → {c.corrected}")
        else:
            print(c.corrected)