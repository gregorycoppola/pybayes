# src/qbbn/cli/commands/doc.py
"""
Document management commands.
"""

import redis

from qbbn.core.document import DocumentStore


def add_subparser(subparsers):
    parser = subparsers.add_parser("doc", help="Document management")
    doc_sub = parser.add_subparsers(dest="doc_command", required=True)
    
    # add
    add_p = doc_sub.add_parser("add", help="Add a document")
    add_p.add_argument("text", help="Document text")
    add_p.add_argument("--db", type=int, default=0)
    add_p.set_defaults(func=doc_add)
    
    # list
    list_p = doc_sub.add_parser("list", help="List all documents")
    list_p.add_argument("--db", type=int, default=0)
    list_p.set_defaults(func=doc_list)
    
    # show
    show_p = doc_sub.add_parser("show", help="Show document details")
    show_p.add_argument("doc_id", help="Document ID")
    show_p.add_argument("--db", type=int, default=0)
    show_p.set_defaults(func=doc_show)
    
    # search
    search_p = doc_sub.add_parser("search", help="Search documents")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--db", type=int, default=0)
    search_p.set_defaults(func=doc_search)
    
    # delete
    del_p = doc_sub.add_parser("delete", help="Delete a document")
    del_p.add_argument("doc_id", help="Document ID")
    del_p.add_argument("--db", type=int, default=0)
    del_p.set_defaults(func=doc_delete)


def doc_add(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    store = DocumentStore(client)
    doc_id = store.add(args.text)
    print(doc_id)


def doc_list(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    store = DocumentStore(client)
    docs = store.list_all()
    
    if not docs:
        print("No documents")
        return
    
    for doc in docs:
        preview = doc.text[:50] + "..." if len(doc.text) > 50 else doc.text
        print(f"{doc.id}  {preview}")


def doc_show(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    store = DocumentStore(client)
    
    doc = store.get(args.doc_id)
    if not doc:
        print(f"Document {args.doc_id} not found")
        return
    
    print(f"ID: {doc.id}")
    print(f"Created: {doc.created_at}")
    print(f"Text: {doc.text}")
    
    stages = store.list_stages(args.doc_id)
    if stages:
        print(f"\nProcessed stages: {', '.join(stages)}")
        for stage in stages:
            data = store.get_data(args.doc_id, stage)
            print(f"\n=== {stage} ===")
            if isinstance(data, list) and len(data) > 5:
                print(f"  ({len(data)} items)")
            else:
                import json
                print(json.dumps(data, indent=2)[:500])


def doc_search(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    store = DocumentStore(client)
    docs = store.search(args.query)
    
    if not docs:
        print(f"No documents matching '{args.query}'")
        return
    
    for doc in docs:
        preview = doc.text[:50] + "..." if len(doc.text) > 50 else doc.text
        print(f"{doc.id}  {preview}")


def doc_delete(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    store = DocumentStore(client)
    
    if store.delete(args.doc_id):
        print(f"Deleted {args.doc_id}")
    else:
        print(f"Document {args.doc_id} not found")