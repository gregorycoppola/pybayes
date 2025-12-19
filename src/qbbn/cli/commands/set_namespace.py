# src/qbbn/cli/commands/set_namespace.py
"""
Set the global namespace.
"""

import redis

from qbbn.core.state import set_namespace


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "set-namespace",
        help="Set the global namespace."
    )
    parser.add_argument("namespace", help="Namespace name.")
    parser.add_argument("--db", type=int, default=0)
    parser.set_defaults(func=run)


def run(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    set_namespace(client, args.namespace)
    print(f"Namespace set to: {args.namespace}")