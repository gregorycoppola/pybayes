# src/qbbn/cli/commands/add_text.py
"""
Add raw text to the pipeline, returns a UUID handle.
"""

import redis

from qbbn.core.pipeline import Pipeline


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "add-text",
        help="Add raw text to the pipeline, returns UUID."
    )
    parser.add_argument("text", help="The text to add.")
    parser.add_argument("--db", type=int, default=0)
    parser.set_defaults(func=run)


def run(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    pipeline = Pipeline(client)
    
    example_id = pipeline.add(args.text)
    print(example_id)