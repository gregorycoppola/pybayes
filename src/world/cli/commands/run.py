"""
Run commands.
"""

import sys
from world.cli import client


def add_subparser(subparsers):
    parser = subparsers.add_parser("run", help="Annotation runs")
    run_sub = parser.add_subparsers(dest="run_command", required=True)
    
    # create
    create_p = run_sub.add_parser("create", help="Create a new run")
    create_p.add_argument("doc_id", help="Document ID")
    create_p.add_argument("kb_id", help="Knowledge Base ID")
    create_p.add_argument("--from", dest="parent", help="Branch from existing run")
    create_p.set_defaults(func=run_create)
    
    # process
    proc_p = run_sub.add_parser("process", help="Process a run")
    proc_p.add_argument("run_id", help="Run ID")
    proc_p.add_argument("--layers", nargs="+", help="Specific layers to run")
    proc_p.set_defaults(func=run_process)
    
    # show
    show_p = run_sub.add_parser("show", help="Show run info")
    show_p.add_argument("run_id", help="Run ID")
    show_p.set_defaults(func=run_show)
    
    # show-all
    showall_p = run_sub.add_parser("show-all", help="Show all layer DSLs for a run")
    showall_p.add_argument("run_id", help="Run ID")
    showall_p.set_defaults(func=run_show_all)
    
    # list
    list_p = run_sub.add_parser("list", help="List runs for a document")
    list_p.add_argument("doc_id", help="Document ID")
    list_p.set_defaults(func=run_list)
    
    # layer
    layer_p = run_sub.add_parser("layer", help="Show layer DSL for a run")
    layer_p.add_argument("run_id", help="Run ID")
    layer_p.add_argument("layer_id", help="Layer ID")
    layer_p.set_defaults(func=run_layer)


def run_create(args):
    try:
        result = client.create_run(args.doc_id, args.kb_id, args.parent)
        print(f"✓ Created run: {result['id']}")
        print(f"  doc: {result['doc_id']}")
        print(f"  kb: {result['kb_id']}")
        if result.get('parent_run_id'):
            print(f"  branched from: {result['parent_run_id']}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def run_process(args):
    try:
        result = client.process_run(args.run_id, args.layers)
        print(f"Run: {result['run_id']}")
        print()
        for lid, r in result["results"].items():
            icon = "✓" if r["success"] else "✗"
            print(f"{icon} {lid}: {r['message']}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def run_show(args):
    try:
        run = client.get_run(args.run_id)
        print(f"Run: {run['id']}")
        print(f"Doc: {run['doc_id']}")
        print(f"KB: {run['kb_id']} ({run.get('kb_name', '?')})")
        if run.get('parent_run_id'):
            print(f"Parent: {run['parent_run_id']}")
        print(f"Created: {run['created_at']}")
        print(f"Text: {run.get('doc_text', '')[:60]}...")
        print()
        print("Layers:")
        for lid, layer in run["layers"].items():
            icon = "✓" if layer["status"] == "done" else "○"
            print(f"  {icon} {lid}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def run_show_all(args):
    try:
        run = client.get_run(args.run_id)
        
        print(f"{'=' * 60}")
        print(f"Run: {run['id']}")
        print(f"Doc: {run['doc_id']}")
        print(f"KB: {run['kb_id']} ({run.get('kb_name', '?')})")
        print(f"Text: {run.get('doc_text', '')}")
        print(f"{'=' * 60}")
        print()
        
        # Get layer order from API
        layers_info = client.list_layers()
        layer_order = [l['id'] for l in layers_info]
        
        for lid in layer_order:
            layer_status = run["layers"].get(lid, {})
            if layer_status.get("status") != "done":
                print(f"--- {lid} (not run) ---")
                print()
                continue
            
            try:
                result = client.get_run_layer_dsl(args.run_id, lid)
                print(f"--- {lid}{result['ext']} ---")
                print(result["dsl"])
                print()
            except:
                print(f"--- {lid} (error) ---")
                print()
                
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def run_list(args):
    try:
        runs = client.list_runs(args.doc_id)
        if not runs:
            print("No runs for this document.")
            return
        for r in runs:
            parent = f" (from {r['parent_run_id'][:8]})" if r.get('parent_run_id') else ""
            print(f"{r['id']}  kb:{r['kb_id']}{parent}  {r['created_at'][:19]}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def run_layer(args):
    try:
        result = client.get_run_layer_dsl(args.run_id, args.layer_id)
        print(f"# {args.run_id} / {result['layer_id']}{result['ext']}")
        print()
        print(result["dsl"])
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)