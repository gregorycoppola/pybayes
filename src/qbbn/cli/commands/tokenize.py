# src/qbbn/cli/commands/tokenize.py
"""
Tokenize an example by UUID.
"""

import redis

from qbbn.core.pipeline import Pipeline


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "tokenize",
        help="Tokenize an example."
    )
    parser.add_argument("example_id", help="The example UUID.")
    parser.add_argument("--db", type=int, default=0)
    parser.set_defaults(func=run)


def run(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    pipeline = Pipeline(client)
    
    tokens = pipeline.run_tokenize(args.example_id)
    
    for t in tokens:
        print(f"{t.position:3d}: {t.text}")