"""
Document commands.
"""

import sys
from rich import print_json
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
    
    # json
    json_p = doc_sub.add_parser("json", help="Show document with all layers as JSON")
    json_p.add_argument("doc_id", help="Document ID")
    json_p.set_defaults(func=doc_json)


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
        if doc.get("layers"):
            print(f"Layers: {', '.join(doc['layers'])}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def doc_json(args):
    try:
        doc = client.get_doc(args.doc_id)
        
        # Build full document with layers
        result = {
            "id": doc["id"],
            "text": doc["text"],
            "created_at": doc["created_at"],
            "layers": {}
        }
        
        # Fetch each computed layer
        for layer_id in doc.get("layers", []):
            try:
                layer_data = client.get_layer_data(args.doc_id, layer_id)
                result["layers"][layer_id] = layer_data["data"]
            except Exception:
                result["layers"][layer_id] = None
        
        print_json(data=result)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)