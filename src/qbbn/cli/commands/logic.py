# src/qbbn/cli/commands/logic.py
"""
Logical language commands.
"""

import redis
import sys

from qbbn.core.document import DocumentStore
from qbbn.core.logical_lang import parse_logical, format_document, ParseError


def add_subparser(subparsers):
    parser = subparsers.add_parser("logic", help="Logical language tools")
    logic_sub = parser.add_subparsers(dest="logic_command", required=True)
    
    # parse - parse from stdin or string
    parse_p = logic_sub.add_parser("parse", help="Parse logical language")
    parse_p.add_argument("--text", "-t", help="Text to parse (otherwise reads stdin)")
    parse_p.set_defaults(func=logic_parse)
    
    # load - parse and store as a logical document
    load_p = logic_sub.add_parser("load", help="Load logical document into store")
    load_p.add_argument("--text", "-t", help="Text to parse (otherwise reads stdin)")
    load_p.add_argument("--db", type=int, default=0)
    load_p.set_defaults(func=logic_load)
    
    # example - show example syntax
    example_p = logic_sub.add_parser("example", help="Show example syntax")
    example_p.set_defaults(func=logic_example)


def logic_parse(args):
    if args.text:
        text = args.text
    else:
        print("Enter logical language (Ctrl+D to finish):")
        text = sys.stdin.read()
    
    try:
        doc = parse_logical(text)
        print("\n=== Parsed ===")
        print(format_document(doc))
        print(f"\n=== Summary ===")
        print(f"Entities: {len(doc.entities)}")
        print(f"Propositions: {len(doc.propositions)}")
        print(f"Rules: {len(doc.rules)}")
        print(f"Queries: {len(doc.queries)}")
    except ParseError as e:
        print(f"Parse error: {e}")


def logic_load(args):
    if args.text:
        text = args.text
    else:
        print("Enter logical language (Ctrl+D to finish):")
        text = sys.stdin.read()
    
    try:
        doc = parse_logical(text)
        
        client = redis.Redis(host="localhost", port=6379, db=args.db)
        store = DocumentStore(client)
        
        # Store as a special logical document
        doc_id = store.add(text)
        
        # Store parsed components
        store.set_data(doc_id, "logical-parsed", {
            "entities": {k: {"entity": v.entity.id, "type": v.type.name} for k, v in doc.entities.items()},
            "propositions": [p.to_dict() for p in doc.propositions],
            "rules": [r.to_dict() for r in doc.rules],
            "queries": [q.to_dict() for q in doc.queries],
        })
        
        print(f"Loaded: {doc_id}")
        print(f"  {len(doc.entities)} entities")
        print(f"  {len(doc.propositions)} propositions")
        print(f"  {len(doc.rules)} rules")
        print(f"  {len(doc.queries)} queries")
        
    except ParseError as e:
        print(f"Parse error: {e}")


def logic_example(args):
    example = """# Example logical language document

# Declare entities with their types
entity socrates : person
entity plato : person
entity athens : place

# State facts (grounded propositions)
man(theme: socrates)
philosopher(theme: socrates)
philosopher(theme: plato)
in(theme: socrates, location: athens)

# Define rules (implications with variables)
rule [x:person]:
  man(theme: x) -> mortal(theme: x)

rule [x:person]:
  philosopher(theme: x) -> wise(theme: x)

# Query (what do we want to know?)
? mortal(theme: socrates)
? wise(theme: plato)
"""
    print(example)