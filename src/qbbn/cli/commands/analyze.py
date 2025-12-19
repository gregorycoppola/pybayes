# src/qbbn/cli/commands/analyze.py
"""
Run sentence analysis (verb + arguments) - recursive.
"""

import json
import redis
from openai import OpenAI

from qbbn.core.pipeline import Pipeline
from qbbn.core.analysis import TextAnalysis
from qbbn.core.analyze_verb import analyze_verb
from qbbn.core.analyze_args import analyze_args


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "analyze",
        help="Analyze sentence structure (requires segment first)."
    )
    parser.add_argument("example_id", help="The example UUID.")
    parser.add_argument("--db", type=int, default=0)
    parser.set_defaults(func=run)


def print_analysis(analysis, tokens, indent=0):
    """Recursively print analysis."""
    prefix = "  " * indent
    
    if analysis.verb_index is not None:
        verb = tokens[analysis.verb_index]
        print(f"{prefix}verb: {verb} (index {analysis.verb_index})")
        print(f"{prefix}tense: {analysis.tense.value if analysis.tense else 'N/A'}")
        print(f"{prefix}aspect: {analysis.aspect.value if analysis.aspect else 'N/A'}")
        print(f"{prefix}mood: {analysis.mood.value if analysis.mood else 'N/A'}")
        if analysis.negated:
            print(f"{prefix}negated: yes")
    
    if analysis.arguments:
        print(f"{prefix}arguments:")
        for arg in analysis.arguments:
            span = " ".join(tokens[arg.start:arg.end])
            print(f"{prefix}  {arg.role}: \"{span}\" [{arg.start}:{arg.end}] ({arg.arg_type.value})")
            if arg.nested:
                print(f"{prefix}    nested analysis:")
                # Get nested tokens
                nested_tokens = tokens[arg.start:arg.end]
                print_analysis(arg.nested, tokens, indent + 3)


def run(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    pipeline = Pipeline(client)
    openai_client = OpenAI()
    
    corrected = pipeline.get_corrected(args.example_id)
    segments = pipeline.get_segments(args.example_id)
    
    if corrected is None:
        print(f"No corrected tokens for {args.example_id}, run correct first")
        return
    
    if segments is None:
        print(f"No segments for {args.example_id}, run segment first")
        return
    
    tokens = [t.corrected for t in corrected]
    
    text_analysis = TextAnalysis()
    
    for i, (start, end) in enumerate(segments):
        sent_tokens = tokens[start:end]
        print(f"\n--- Sentence {i+1}: \"{' '.join(sent_tokens)}\" ---")
        
        # Step 1: verb
        print("Finding main verb...")
        analysis = analyze_verb(sent_tokens, start, end, openai_client)
        
        # Step 2: arguments (recursive)
        print("Finding arguments...")
        analysis = analyze_args(sent_tokens, analysis, openai_client, recursive=True)
        
        print_analysis(analysis, tokens)
        
        text_analysis.sentences.append(analysis)
    
    pipeline.store_text_analysis(args.example_id, text_analysis)
    print("\nStored text analysis.")