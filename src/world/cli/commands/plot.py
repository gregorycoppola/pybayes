# src/world/cli/commands/plot.py
"""Plot BP convergence from CSV."""

import sys
from pathlib import Path


def add_subparser(subparsers):
    parser = subparsers.add_parser("plot", help="Plot convergence from CSV")
    parser.add_argument("csv_file", help="Path to CSV file from --csv output")
    parser.add_argument("--output", "-o", help="Output PNG path (default: same as csv but .png)")
    parser.add_argument("--no-show", action="store_true", help="Don't display plot")
    parser.set_defaults(func=run_plot)


def run_plot(args):
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
    except ImportError:
        print("Need pandas and matplotlib. Run:")
        print("  uv add pandas matplotlib")
        return
    
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        return
    
    df = pd.read_csv(csv_path)
    
    plt.figure(figsize=(10, 6))
    
    for col in df.columns[1:]:  # skip 'iteration'
        plt.plot(df['iteration'], df[col], label=col, marker='o', markersize=3)
    
    plt.xlabel('Iteration')
    plt.ylabel('P(true)')
    plt.title(f'Belief Propagation Convergence - {csv_path.stem}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 1.05)
    
    out_path = args.output or str(csv_path).replace('.csv', '.png')
    plt.savefig(out_path, dpi=150)
    print(f"Saved to {out_path}")
    
    if not args.no_show:
        plt.show()