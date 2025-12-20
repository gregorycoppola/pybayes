# src/qbbn/cli/commands/infer.py
"""
Inference commands.
"""

from pathlib import Path

from qbbn.core.logical_lang import parse_logical, format_predicate, ParseError
from qbbn.core.horn import KnowledgeBase
from qbbn.core.proposition_graph import PropositionGraph
from qbbn.core.inference import forward_chain, query


def add_subparser(subparsers):
    parser = subparsers.add_parser("infer", help="Run inference on a .logic file")
    parser.add_argument("file", help="Path to .logic file")
    parser.add_argument("--iterations", "-i", type=int, default=10, help="Max iterations")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show graph details")
    parser.set_defaults(func=run_infer)


def run_infer(args):
    try:
        text = Path(args.file).read_text()
        doc = parse_logical(text)
        
        # Build knowledge base and ground
        kb = KnowledgeBase.from_logical_document(doc)
        
        # Build proposition graph
        graph = PropositionGraph.from_knowledge_base(kb)
        
        print(f"=== Graph Stats ===")
        stats = graph.stats()
        print(f"  Propositions: {stats['propositions']}")
        print(f"  Conjunctions: {stats['conjunctions']}")
        print(f"  Evidence: {stats['evidence']}")
        
        if args.verbose:
            print()
            graph.print_graph()
        
        # Run inference
        print(f"\n=== Running Inference ===")
        forward_chain(graph, iterations=args.iterations)
        
        # Show queries
        if doc.queries:
            print(f"\n=== Query Results ===")
            for q in doc.queries:
                prob = query(graph, q)
                status = "TRUE" if prob > 0.9 else "FALSE" if prob < 0.1 else f"{prob:.2f}"
                print(f"  {format_predicate(q)}: {status}")
        
        # Show all high-probability propositions
        print(f"\n=== Inferred (P > 0.5) ===")
        for key, node in sorted(graph.propositions.items()):
            if node.prob_true > 0.5 and not node.is_evidence:
                print(f"  {key}: {node.prob_true:.2f}")
        
    except FileNotFoundError:
        print(f"File not found: {args.file}")
    except ParseError as e:
        print(f"Parse error: {e}")