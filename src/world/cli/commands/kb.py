"""
Knowledge Base commands.
"""

import sys
from pathlib import Path
from world.cli import client


def add_subparser(subparsers):
    parser = subparsers.add_parser("kb", help="Knowledge base management")
    kb_sub = parser.add_subparsers(dest="kb_command", required=True)
    
    # add (from file)
    add_p = kb_sub.add_parser("add", help="Add KB from .logic file")
    add_p.add_argument("file", help="Path to .logic file")
    add_p.add_argument("--name", help="KB name (default: filename)")
    add_p.set_defaults(func=kb_add)
    
    # list
    list_p = kb_sub.add_parser("list", help="List all KBs")
    list_p.set_defaults(func=kb_list)
    
    # show
    show_p = kb_sub.add_parser("show", help="Show KB details")
    show_p.add_argument("kb_id", help="KB ID")
    show_p.set_defaults(func=kb_show)
    
    # dsl
    dsl_p = kb_sub.add_parser("dsl", help="Show KB as DSL")
    dsl_p.add_argument("kb_id", help="KB ID")
    dsl_p.set_defaults(func=kb_dsl)


def kb_add(args):
    path = Path(args.file)
    if not path.exists():
        print(f"✗ File not found: {args.file}")
        sys.exit(1)
    
    dsl = path.read_text()
    name = args.name or path.stem
    
    try:
        result = client.create_kb(name, dsl)
        print(f"✓ Created KB: {result['id']}")
        print(f"  name: {result['name']}")
        print(f"  entities: {result['entity_count']}")
        print(f"  facts: {result['fact_count']}")
        print(f"  rules: {result['rule_count']}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def kb_list(args):
    try:
        kbs = client.list_kbs()
        if not kbs:
            print("No knowledge bases.")
            return
        for kb in kbs:
            print(f"{kb['id']}  {kb['name']:20} ({kb['entity_count']} ent, {kb['fact_count']} facts, {kb['rule_count']} rules)")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def kb_show(args):
    try:
        kb = client.get_kb(args.kb_id)
        print(f"ID: {kb['id']}")
        print(f"Name: {kb['name']}")
        print(f"Created: {kb['created_at']}")
        print()
        print(f"Entities ({len(kb['entities'])}):")
        for eid, ent in kb['entities'].items():
            print(f"  {eid} : {ent['type']}")
        print()
        print(f"Facts ({len(kb['facts'])}):")
        for fact in kb['facts']:
            args_str = ", ".join(f"{k}: {v}" for k, v in fact['args'].items())
            print(f"  {fact['predicate']}({args_str})")
        print()
        print(f"Rules ({len(kb['rules'])}):")
        for rule in kb['rules']:
            vars_str = ", ".join(f"{v}:{t}" for v, t in rule['variables'])
            prem = f"{rule['premise']['predicate']}(...)"
            conc = f"{rule['conclusion']['predicate']}(...)"
            print(f"  [{vars_str}]: {prem} -> {conc}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def kb_dsl(args):
    try:
        result = client.get_kb_dsl(args.kb_id)
        print(f"# {result['name']} ({args.kb_id})")
        print()
        print(result['dsl'])
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)