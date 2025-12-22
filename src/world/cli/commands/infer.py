"""Inference commands."""

import typer
from rich.console import Console

app = typer.Typer(help="Run belief propagation inference")
console = Console()


@app.callback(invoke_without_command=True)
def infer(
    ctx: typer.Context,
    kb_path: str = typer.Argument(..., help="Path to .logic file"),
    iterations: int = typer.Option(20, "--iterations", "-n", help="Max BP iterations"),
    damping: float = typer.Option(0.5, "--damping", "-d", help="Damping factor"),
    graph: bool = typer.Option(False, "--graph", "-g", help="Show factor graph structure"),
    table: bool = typer.Option(True, "--table/--no-table", "-t", help="Show belief table"),
    spark: bool = typer.Option(True, "--spark/--no-spark", "-s", help="Show convergence sparkline"),
    summary: bool = typer.Option(False, "--summary", help="Show convergence summary"),
    query_prop: str = typer.Option(None, "--query", "-q", help="Query specific proposition"),
    csv_out: str = typer.Option(None, "--csv", help="Write beliefs to CSV"),
):
    """Run belief propagation on a knowledge base."""
    from world.core.horn import KnowledgeBase
    from world.core.factor_graph import FactorGraph, belief_propagation, BPTrace, query
    
    # Load KB
    kb = KnowledgeBase.from_file(kb_path)
    console.print(f"[dim]Loaded {len(kb.clauses)} clauses from {kb_path}[/dim]")
    
    # Build factor graph
    fg = FactorGraph.from_knowledge_base(kb)
    stats = fg.stats()
    console.print(f"[dim]Graph: {stats['variables']} vars, {stats['factors']} factors, {stats['evidence']} evidence[/dim]")
    
    # Run BP
    trace = BPTrace()
    belief_propagation(fg, iterations=iterations, damping=damping, trace=trace)
    console.print(f"[dim]Ran {len(trace.iterations)} iterations[/dim]\n")
    
    # Display
    if graph:
        trace.print_graph(fg)
        console.print()
    
    if table:
        trace.print_beliefs_table()
        console.print()
    
    if spark:
        trace.print_convergence_spark()
        console.print()
    
    if summary:
        trace.print_summary()
        console.print()
    
    if query_prop:
        p = query(fg, query_prop)
        console.print(f"[bold]P({query_prop}) = {p:.4f}[/bold]")
    
    if csv_out:
        trace.to_csv(csv_out)
        console.print(f"[dim]Wrote {csv_out}[/dim]")