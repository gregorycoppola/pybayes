"""
QBBN CLI.
"""

import argparse
from world.cli.commands import doc, kb, run, layer


def main():
    parser = argparse.ArgumentParser(prog="world", description="QBBN CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    doc.add_subparser(subparsers)
    kb.add_subparser(subparsers)
    run.add_subparser(subparsers)
    layer.add_subparser(subparsers)
    
    args = parser.parse_args()
    
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()