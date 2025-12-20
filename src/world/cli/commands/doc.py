"""
Document commands.
"""

import sys
from world.cli import client


def add_subparser(subparsers):
    parser = subparsers.add_parser("doc", help="Document management")
    doc_sub = parser.add_subparsers(dest="doc_command", required=True)
    
    # add
    add_p = doc_sub.add_parser("add", help="Add a new document")
    add_p.add_argument("text", help="Document text")
    add_p.set_defaults(func=doc_add)
    
    # list
    list_p = doc_sub.add_parser("list", help="List all documents")
    list_p.set_defaults(func=doc_list)
    
    # show
    show_p = doc_sub.add_parser("show", help="Show a document")
    show_p.add_argument("doc_id", help="Document ID")
    show_p.set_defaults(func=doc_show)


def doc_add(args):
    try:
        result = client.create_doc(args.text)
        print(f"✓ Created: {result['id']}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def doc_list(args):
    try:
        docs = client.list_docs()
        if not docs:
            print("No documents.")
            return
        for d in docs:
            text_preview = d["text"][:50] + "..." if len(d["text"]) > 50 else d["text"]
            print(f"{d['id'][:12]}  {text_preview}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def doc_show(args):
    try:
        doc = client.get_doc(args.doc_id)
        print(f"ID: {doc['id']}")
        print(f"Text: {doc['text']}")
        print(f"Created: {doc['created_at']}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)