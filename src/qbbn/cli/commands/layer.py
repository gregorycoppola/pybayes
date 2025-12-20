"""
Layer management commands.
"""

import redis
from pathlib import Path
from openai import OpenAI

from qbbn.core.document import DocumentStore
from qbbn.core.layers import list_layers, get_layer, resolve_dependencies
from qbbn.core.layers.runner import LayerRunner

# Import all layers to register them
import qbbn.core.layers.base
import qbbn.core.layers.clauses
import qbbn.core.layers.args
import qbbn.core.layers.coref
import qbbn.core.layers.logic
import qbbn.core.layers.ground


def add_subparser(subparsers):
    parser = subparsers.add_parser("layer", help="Layer management")
    layer_sub = parser.add_subparsers(dest="layer_command", required=True)
    
    # list
    list_p = layer_sub.add_parser("list", help="List all registered layers")
    list_p.set_defaults(func=layer_list)
    
    # run
    run_p = layer_sub.add_parser("run", help="Run layers on a document")
    run_p.add_argument("doc_id", help="Document ID")
    run_p.add_argument("layers", nargs="+", help="Layer IDs to run")
    run_p.add_argument("--force", "-f", action="store_true", help="Force re-run")
    run_p.add_argument("--db", type=int, default=0)
    run_p.set_defaults(func=layer_run)
    
    # show
    show_p = layer_sub.add_parser("show", help="Show layer data as DSL")
    show_p.add_argument("doc_id", help="Document ID")
    show_p.add_argument("layer_id", help="Layer ID")
    show_p.add_argument("--db", type=int, default=0)
    show_p.set_defaults(func=layer_show)
    
    # show-all
    showall_p = layer_sub.add_parser("show-all", help="Show all layer data for a document")
    showall_p.add_argument("doc_id", help="Document ID")
    showall_p.add_argument("--db", type=int, default=0)
    showall_p.set_defaults(func=layer_show_all)
    
    # set
    set_p = layer_sub.add_parser("set", help="Set layer override from file")
    set_p.add_argument("doc_id", help="Document ID")
    set_p.add_argument("layer_id", help="Layer ID")
    set_p.add_argument("file", help="DSL file to load")
    set_p.add_argument("--db", type=int, default=0)
    set_p.set_defaults(func=layer_set)
    
    # clear
    clear_p = layer_sub.add_parser("clear", help="Clear layer override")
    clear_p.add_argument("doc_id", help="Document ID")
    clear_p.add_argument("layer_id", help="Layer ID")
    clear_p.add_argument("--db", type=int, default=0)
    clear_p.set_defaults(func=layer_clear)


def layer_list(args):
    print("Registered layers:\n")
    for lid in list_layers():
        layer = get_layer(lid)
        deps = ", ".join(layer.depends_on) if layer.depends_on else "(none)"
        print(f"  {lid}")
        print(f"    ext: {layer.ext}")
        print(f"    depends_on: {deps}")
        print()


def layer_run(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    store = DocumentStore(client)
    openai_client = OpenAI()
    
    doc = store.get(args.doc_id)
    if not doc:
        print(f"Document not found: {args.doc_id}")
        return
    
    print(f"Document: {args.doc_id}")
    print(f"Text: {doc.text[:60]}{'...' if len(doc.text) > 60 else ''}")
    print()
    
    all_layers = resolve_dependencies(args.layers)
    print(f"Layers to run: {' → '.join(all_layers)}")
    print()
    
    runner = LayerRunner(store, {"openai": openai_client})
    results = runner.run(args.doc_id, args.layers, force=args.force)
    
    for lid, result in results.items():
        status = "✓" if result.success else "✗"
        print(f"{status} {lid}: {result.message}")


def layer_show(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    store = DocumentStore(client)
    
    runner = LayerRunner(store, {})
    dsl = runner.get_dsl(args.doc_id, args.layer_id)
    
    if dsl is None:
        print(f"No data for layer '{args.layer_id}' on doc '{args.doc_id}'")
        print(f"Run: qbbn layer run {args.doc_id} {args.layer_id}")
        return
    
    layer = get_layer(args.layer_id)
    print(f"# {args.doc_id} / {args.layer_id}{layer.ext}")
    print()
    print(dsl)


def layer_show_all(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    store = DocumentStore(client)
    
    doc = store.get(args.doc_id)
    if not doc:
        print(f"Document not found: {args.doc_id}")
        return
    
    print(f"# Document: {args.doc_id}")
    print(f"# Text: {doc.text}")
    print()
    
    runner = LayerRunner(store, {})
    
    for lid in list_layers():
        dsl = runner.get_dsl(args.doc_id, lid)
        if dsl is not None:
            layer = get_layer(lid)
            print(f"=== {lid}{layer.ext} ===")
            print(dsl)
            print()


def layer_set(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    store = DocumentStore(client)
    
    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {args.file}")
        return
    
    dsl_text = path.read_text()
    
    runner = LayerRunner(store, {})
    errors = runner.set_override(args.doc_id, args.layer_id, dsl_text)
    
    if errors:
        print(f"Validation errors:")
        for e in errors:
            print(f"  - {e}")
    else:
        print(f"✓ Set override for {args.layer_id}")
        print(f"  Downstream layers invalidated")


def layer_clear(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    store = DocumentStore(client)
    
    store.delete_data(args.doc_id, f"{args.layer_id}_override")
    print(f"✓ Cleared override for {args.layer_id}")