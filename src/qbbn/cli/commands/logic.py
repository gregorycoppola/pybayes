# src/qbbn/cli/commands/logic.py
"""
Logical language commands.
"""

import redis
from pathlib import Path

from qbbn.core.document import DocumentStore
from qbbn.core.logical_lang import parse_logical, format_document, format_predicate, ParseError
from qbbn.core.horn import KnowledgeBase, format_horn_clause


def add_subparser(subparsers):
    parser = subparsers.add_parser("logic", help="Logical language tools")
    logic_sub = parser.add_subparsers(dest="logic_command", required=True)
    
    # parse - parse a .logic file
    parse_p = logic_sub.add_parser("parse", help="Parse a .logic file")
    parse_p.add_argument("file", help="Path to .logic file")
    parse_p.add_argument("--ground", action="store_true", help="Show grounded clauses")
    parse_p.set_defaults(func=logic_parse)
    
    # load - parse and store as a logical document
    load_p = logic_sub.add_parser("load", help="Load .logic file into store")
    load_p.add_argument("file", help="Path to .logic file")
    load_p.add_argument("--db", type=int, default=0)
    load_p.set_defaults(func=logic_load)
    
    # example - show example syntax
    example_p = logic_sub.add_parser("example", help="Show example syntax")
    example_p.set_defaults(func=logic_example)


def read_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if p.suffix != ".logic":
        print(f"Warning: expected .logic extension, got {p.suffix}")
    return p.read_text()


def logic_parse(args):
    try:
        text = read_file(args.file)
        doc = parse_logical(text)
        
        print(f"=== {args.file} ===\n")
        print(format_document(doc))
        print(f"\n=== Summary ===")
        print(f"Entities: {len(doc.entities)}")
        print(f"Propositions: {len(doc.propositions)}")
        print(f"Rules: {len(doc.rules)}")
        print(f"Queries: {len(doc.queries)}")
        
        if args.ground:
            kb = KnowledgeBase.from_logical_document(doc)
            grounded = kb.ground_all()
            
            print(f"\n=== Grounded ({len(grounded)} clauses) ===")
            for clause in grounded:
                print(f"  {format_horn_clause(clause, show_vars=False)}")
        
    except FileNotFoundError as e:
        print(e)
    except ParseError as e:
        print(f"Parse error: {e}")


def logic_load(args):
    try:
        text = read_file(args.file)
        doc = parse_logical(text)
        
        client = redis.Redis(host="localhost", port=6379, db=args.db)
        store = DocumentStore(client)
        
        doc_id = store.add(text)
        
        store.set_data(doc_id, "source-file", args.file)
        store.set_data(doc_id, "logical-parsed", {
            "entities": {k: {"entity": v.entity.id, "type": v.type.name} for k, v in doc.entities.items()},
            "propositions": [p.to_dict() for p in doc.propositions],
            "rules": [{"premises": [p.to_dict() for p in r.premises], "conclusion": r.conclusion.to_dict(), "variables": [{"name": v.name, "type": v.type.name} for v in r.variables]} for r in doc.rules],
            "queries": [q.to_dict() for q in doc.queries],
        })
        
        print(f"Loaded: {doc_id}")
        print(f"  File: {args.file}")
        print(f"  {len(doc.entities)} entities")
        print(f"  {len(doc.propositions)} propositions")
        print(f"  {len(doc.rules)} rules")
        print(f"  {len(doc.queries)} queries")
        
    except FileNotFoundError as e:
        print(e)
    except ParseError as e:
        print(f"Parse error: {e}")


def logic_example(args):
    example = """# Example .logic file syntax

# Declare entities with their types
entity socrates : person
entity plato : person

# State facts (grounded propositions)
man(theme: socrates)
man(theme: plato)

# Define rules with conjunctions
rule [x:person]: man(theme: x) -> mortal(theme: x)
rule [x:person, y:person]: like(agent: x, theme: y) & like(agent: y, theme: x) -> date(agent: x, theme: y)

# Query
? mortal(theme: socrates)
"""
    print(example)