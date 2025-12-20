# src/world/cli/commands/infer.py
"""
Inference commands.
"""

from pathlib import Path

from world.core.logical_lang import parse_logical, format_predicate, ParseError
from world.core.horn import KnowledgeBase
from world.core.factor_graph import FactorGraph, belief_propagation, query, BPTrace


def add_subparser(subparsers):
    parser = subparsers.add_parser("infer", help="Run inference on a .logic file")
    parser.add_argument("file", help="Path to .logic file")
    parser.add_argument("--iterations", "-i", type=int, default=20, help="BP iterations")
    parser.add_argument("--damping", "-d", type=float, default=0.5, help="BP damping")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all probabilities")
    parser.add_argument("--trace", "-t", action="store_true", help="Show convergence trace")
    parser.add_argument("--csv", type=str, help="Output beliefs to CSV file")
    parser.add_argument("--csv-messages", type=str, help="Output messages to CSV file")
    parser.set_defaults(func=run_infer)


def run_infer(args):
    try:
        text = Path(args.file).read_text()
        doc = parse_logical(text)
        
        kb = KnowledgeBase.from_logical_document(doc)
        graph = FactorGraph.from_knowledge_base(kb)
        
        print(f"=== Factor Graph ===")
        stats = graph.stats()
        print(f"  Variables: {stats['variables']}")
        print(f"  Factors: {stats['factors']}")
        print(f"  Evidence: {stats['evidence']}")
        
        # Show graph structure
        print(f"\n=== Structure ===")
        for f in graph.factors:
            if f.factor_type == "implication":
                print(f"  f{f.factor_id}: {f.var_keys[0]} → {f.var_keys[1]} [λ={f.weight}]")
            else:
                premises = " ∧ ".join(f.var_keys[:-1])
                print(f"  f{f.factor_id}: {premises} → {f.var_keys[-1]} [λ={f.weight}]")
        
        print(f"\n=== Running BP (iter={args.iterations}, damping={args.damping}) ===")
        trace = belief_propagation(graph, iterations=args.iterations, damping=args.damping)
        
        # Show queries
        if doc.queries:
            print(f"\n=== Query Results ===")
            for q in doc.queries:
                key = format_predicate(q)
                prob = query(graph, key)
                print(f"  {key}: {prob:.4f}")
        
        # Show trace
        if args.trace:
            trace.print_summary()
        
        # CSV output
        if args.csv:
            trace.to_csv(args.csv)
            print(f"\nWrote beliefs to {args.csv}")
        
        if args.csv_messages:
            trace.to_messages_csv(args.csv_messages)
            print(f"Wrote messages to {args.csv_messages}")
        
        # Show all probabilities
        if args.verbose:
            print(f"\n=== All Probabilities ===")
            sorted_vars = sorted(graph.variables.items(), key=lambda x: -x[1].prob_true)
            for key, var in sorted_vars:
                ev = " [E]" if var.is_evidence else ""
                print(f"  {key}: {var.prob_true:.4f}{ev}")
        else:
            print(f"\n=== Inferred (P > 0.5) ===")
            for key, var in sorted(graph.variables.items()):
                if var.prob_true > 0.5 and not var.is_evidence:
                    print(f"  {key}: {var.prob_true:.4f}")
        
    except FileNotFoundError:
        print(f"File not found: {args.file}")
    except ParseError as e:
        print(f"Parse error: {e}")