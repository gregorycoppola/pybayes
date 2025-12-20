# scripts/plot_convergence.py
"""Plot BP convergence from CSV."""

import sys
import pandas as pd
import matplotlib.pyplot as plt

def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_convergence.py results/chain.csv")
        return
    
    df = pd.read_csv(sys.argv[1])
    
    plt.figure(figsize=(10, 6))
    
    for col in df.columns[1:]:  # skip 'iteration'
        plt.plot(df['iteration'], df[col], label=col, marker='o', markersize=3)
    
    plt.xlabel('Iteration')
    plt.ylabel('P(true)')
    plt.title('Belief Propagation Convergence')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 1.05)
    
    out_path = sys.argv[1].replace('.csv', '.png')
    plt.savefig(out_path, dpi=150)
    print(f"Saved to {out_path}")
    plt.show()

if __name__ == "__main__":
    main()