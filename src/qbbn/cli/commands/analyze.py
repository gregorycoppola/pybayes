# src/qbbn/cli/commands/analyze.py
"""
Run sentence analysis (verb + arguments).
"""

import json
import redis
from openai import OpenAI

from qbbn.core.pipeline import Pipeline
from qbbn.core.analyze_verb import analyze_verb
from qbbn.core.analyze_args import analyze_args


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "analyze",
        help="Analyze sentence structure (requires correct first)."
    )
    parser.add_argument("example_id", help="The example UUID.")
    parser.add_argument("--db", type=int, default=0)
    parser.set_defaults(func=run)


def run(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    pipeline = Pipeline(client)
    openai_client = OpenAI()
    
    corrected = pipeline.get_corrected(args.example_id)
    
    if corrected is None:
        print(f"No corrected tokens for {args.example_id}, run correct first")
        return
    
    tokens = [t.corrected for t in corrected]
    
    # Step 1: verb
    print("Finding main verb...")
    analysis = analyze_verb(tokens, openai_client)
    
    if analysis.verb_index is not None:
        print(f"  verb: {tokens[analysis.verb_index]} (index {analysis.verb_index})")
        print(f"  tense: {analysis.tense}")
        print(f"  aspect: {analysis.aspect}")
        print(f"  mood: {analysis.mood}")
        print(f"  negated: {analysis.negated}")
    
    # Step 2: arguments
    print("\nFinding arguments...")
    analysis = analyze_args(tokens, analysis, openai_client)
    
    for arg in analysis.arguments:
        span_tokens = tokens[arg.start:arg.end]
        print(f"  {arg.role}: {' '.join(span_tokens)} [{arg.start}:{arg.end}] ({arg.arg_type})")
    
    # Store
    pipeline.store_analysis(args.example_id, analysis)
    print("\nStored analysis.")