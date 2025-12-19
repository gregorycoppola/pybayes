# src/qbbn/cli/commands/run.py
"""
Run processors on a document.
"""

import redis
from openai import OpenAI

from qbbn.core.document import DocumentStore
from qbbn.core.processors import get_processor, list_processors

# Import to register processors
import qbbn.core.processors_impl


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "run",
        help="Run processors on a document"
    )
    parser.add_argument("doc_id", help="Document ID")
    parser.add_argument("processors", nargs="*", help="Processors to run (in order)")
    parser.add_argument("--all", action="store_true", help="Run all processors")
    parser.add_argument("--force", action="store_true", help="Re-run even if already done")
    parser.add_argument("--list", action="store_true", help="List available processors")
    parser.add_argument("--db", type=int, default=0)
    parser.set_defaults(func=run)


def run(args):
    if args.list:
        print("Available processors:")
        for name in list_processors():
            print(f"  {name}")
        return
    
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    store = DocumentStore(client)
    openai_client = OpenAI()
    
    doc = store.get(args.doc_id)
    if not doc:
        print(f"Document {args.doc_id} not found")
        return
    
    if args.all:
        processors = list_processors()
    elif args.processors:
        processors = args.processors
    else:
        print("Specify processors to run, or use --all")
        print(f"Available: {', '.join(list_processors())}")
        return
    
    print(f"Document: {args.doc_id}")
    print(f"Text: {doc.text[:60]}...")
    print()
    
    for proc_name in processors:
        try:
            proc = get_processor(proc_name, store, openai_client)
            result = proc.run(args.doc_id, force=args.force)
            status = "✓" if result.success else "✗"
            print(f"{status} {result.message}")
        except ValueError as e:
            print(f"✗ {e}")