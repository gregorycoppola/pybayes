"""Inference commands."""

from pathlib import Path
from rich.console import Console

console = Console()


def add_subparser(subparsers):
    parser = subparsers.add_parser("infer", help="Run belief propagation inference")
    parser.add_argument("kb_path", help="Path to .logic file")
    parser.add_argument("-n", "--iterations", type=int, default=20, help="Max BP iterations")
    parser.add_argument("-d", "--damping", type=float, default=0.5, help="Damping factor")
    parser.add_argument("-g", "--graph", action="store_true", help="Show factor graph structure")
    parser.add_argument("-t", "--table", action="store_true", default=True, help="Show belief table")
    parser.add_argument("--no-table", action="store_false", dest="table", help="Hide belief table")
    parser.add_argument("-s", "--spark", action="store_true", default=True, help="Show convergence sparkline")
    parser.add_argument("--no-spark", action="store_false", dest="spark", help="Hide sparkline")
    parser.add_argument("--summary", action="store_true", help="Show convergence summary")
    parser.add_argument("-q", "--query", dest="query_prop", help="Query specific proposition")
    parser.add_argument("--csv", dest="csv_out", help="Write beliefs to CSV")
    parser.set_defaults(func=run_infer)


def run_infer(args):
    from world.core.logical_lang import parse_logical
    from world.core.horn import KnowledgeBase
    from world.core.factor_graph import FactorGraph, belief_propagation, BPTrace, query
    
    # Load and parse DSL
    path = Path(args.kb_path)
    if not path.exists():
        console.print(f"[red]✗ File not found: {args.kb_path}[/red]")
        return
    
    text = path.read_text()
    doc = parse_logical(text)
    kb = KnowledgeBase.from_logical_document(doc)
    
    console.print(f"[dim]Loaded {len(kb.clauses)} clauses from {args.kb_path}[/dim]")
    
    # Build factor graph
    fg = FactorGraph.from_knowledge_base(kb)
    stats = fg.stats()
    console.print(f"[dim]Graph: {stats['variables']} vars, {stats['factors']} factors, {stats['evidence']} evidence[/dim]")
    
    # Run BP
    trace = BPTrace()
    belief_propagation(fg, iterations=args.iterations, damping=args.damping, trace=trace)
    console.print(f"[dim]Ran {len(trace.iterations)} iterations[/dim]\n")
    
    # Display
    if args.graph:
        trace.print_graph(fg)
        console.print()
    
    if args.table:
        trace.print_beliefs_table()
        console.print()
    
    if args.spark:
        trace.print_convergence_spark()
        console.print()
    
    if args.summary:
        trace.print_summary()
        console.print()
    
    if args.query_prop:
        p = query(fg, args.query_prop)
        console.print(f"[bold]P({args.query_prop}) = {p:.4f}[/bold]")
    
    if args.csv_out:
        trace.to_csv(args.csv_out)
        console.print(f"[dim]Wrote {args.csv_out}[/dim]")