# src/qbbn/cli/commands/run_pipeline.py
"""
Run the full pipeline on text.
"""

import subprocess
import sys


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "run-pipeline",
        help="Run full pipeline: add-text → tokenize → correct → segment → wsd → analyze"
    )
    parser.add_argument("text", help="The text to process.")
    parser.add_argument("--db", type=int, default=0)
    parser.add_argument("--skip-wsd", action="store_true", help="Skip WSD step")
    parser.set_defaults(func=run)


def call(cmd: list[str]) -> str | None:
    """Run a qbbn command, return stdout."""
    result = subprocess.run(
        [sys.executable, "-m", "qbbn.cli.main"] + cmd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error running: qbbn {' '.join(cmd)}")
        print(result.stderr)
        return None
    return result.stdout.strip()


def run(args):
    db_args = ["--db", str(args.db)]
    
    # Step 1: add-text
    print(f"=== add-text ===")
    example_id = call(["add-text", args.text] + db_args)
    if not example_id:
        return
    print(f"Created: {example_id}")
    
    # Step 2: tokenize
    print(f"\n=== tokenize ===")
    out = call(["tokenize", example_id] + db_args)
    if out is None:
        return
    print(out)
    
    # Step 3: correct
    print(f"\n=== correct ===")
    out = call(["correct", example_id] + db_args)
    if out is None:
        return
    print(out)
    
    # Step 4: segment
    print(f"\n=== segment ===")
    out = call(["segment", example_id] + db_args)
    if out is None:
        return
    print(out)
    
    # Step 5: wsd (optional)
    if not args.skip_wsd:
        print(f"\n=== wsd ===")
        out = call(["wsd", example_id] + db_args)
        if out is None:
            return
        print(out)
    
    # Step 6: analyze
    print(f"\n=== analyze ===")
    out = call(["analyze", example_id] + db_args)
    if out is None:
        return
    print(out)
    
    # Final summary
    print(f"\n=== done ===")
    print(f"Example ID: {example_id}")
    print(f"Run 'qbbn show {example_id}' to see full state")