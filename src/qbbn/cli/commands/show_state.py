# src/qbbn/cli/commands/show_state.py
"""
Show global state.
"""

import redis

from qbbn.core.state import get_namespace


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "show-state",
        help="Show global state."
    )
    parser.add_argument("--db", type=int, default=0)
    parser.set_defaults(func=run)


def run(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    namespace = get_namespace(client)
    print(f"Namespace: {namespace}")