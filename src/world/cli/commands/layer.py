"""
Layer commands - via API.
"""

import sys
import json
from pathlib import Path
from rich import print_json
from world.cli import client


def add_subparser(subparsers):
    parser = subparsers.add_parser("layer", help="Layer management")
    layer_sub = parser.add_subparsers(dest="layer_command", required=True)
    
    # list
    list_p = layer_sub.add_parser("list", help="List all registered layers")
    list_p.set_defaults(func=layer_list)
    
    # run
    run_p = layer_sub.add_parser("run", help="Run a layer on a document")
    run_p.add_argument("doc_id", help="Document ID")
    run_p.add_argument("layer_id", help="Layer ID")
    run_p.add_argument("--force", "-f", action="store_true", help="Force re-run")
    run_p.set_defaults(func=layer_run)
    
    # show (DSL)
    show_p = layer_sub.add_parser("show", help="Show layer data as DSL")
    show_p.add_argument("doc_id", help="Document ID")
    show_p.add_argument("layer_id", help="Layer ID")
    show_p.set_defaults(func=layer_show)
    
    # json
    json_p = layer_sub.add_parser("json", help="Show layer data as JSON")
    json_p.add_argument("doc_id", help="Document ID")
    json_p.add_argument("layer_id", help="Layer ID")
    json_p.set_defaults(func=layer_json)
    
    # set
    set_p = layer_sub.add_parser("set", help="Set layer override from file")
    set_p.add_argument("doc_id", help="Document ID")
    set_p.add_argument("layer_id", help="Layer ID")
    set_p.add_argument("file", help="DSL file to load")
    set_p.set_defaults(func=layer_set)
    
    # clear
    clear_p = layer_sub.add_parser("clear", help="Clear layer override")
    clear_p.add_argument("doc_id", help="Document ID")
    clear_p.add_argument("layer_id", help="Layer ID")
    clear_p.set_defaults(func=layer_clear)


def layer_list(args):
    try:
        layers = client.list_layers()
        print("Registered layers:\n")
        for layer in layers:
            deps = ", ".join(layer["depends_on"]) if layer["depends_on"] else "(none)"
            print(f"  {layer['id']}")
            print(f"    ext: {layer['ext']}")
            print(f"    depends_on: {deps}")
            print()
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def layer_run(args):
    try:
        result = client.run_layer(args.doc_id, args.layer_id, force=args.force)
        icon = "✓" if result["success"] else "✗"
        print(f"{icon} {result['layer_id']}: {result['message']}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def layer_show(args):
    try:
        result = client.get_layer_dsl(args.doc_id, args.layer_id)
        print(f"# {args.doc_id} / {result['layer_id']}{result['ext']}")
        print()
        print(result["dsl"])
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def layer_json(args):
    try:
        result = client.get_layer_data(args.doc_id, args.layer_id)
        print_json(data=result["data"])
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def layer_set(args):
    path = Path(args.file)
    if not path.exists():
        print(f"✗ File not found: {args.file}")
        sys.exit(1)
    
    dsl_text = path.read_text()
    
    try:
        result = client.set_layer_override(args.doc_id, args.layer_id, dsl_text)
        if result.get("success"):
            print(f"✓ Set override for {args.layer_id}")
        else:
            print(f"✗ Validation errors:")
            for e in result.get("errors", []):
                print(f"  - {e}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def layer_clear(args):
    try:
        client.clear_layer_override(args.doc_id, args.layer_id)
        print(f"✓ Cleared override for {args.layer_id}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)