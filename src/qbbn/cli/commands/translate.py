# src/qbbn/cli/commands/translate.py
"""
Translate analysis to logical form.
"""

import json
import redis

from qbbn.core.pipeline import Pipeline
from qbbn.core.translate import translate_analysis, format_predicate


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "translate",
        help="Translate analysis to logical form (requires analyze first)."
    )
    parser.add_argument("example_id", help="The example UUID.")
    parser.add_argument("--db", type=int, default=0)
    parser.set_defaults(func=run)


def run(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    pipeline = Pipeline(client)
    
    corrected = pipeline.get_corrected(args.example_id)
    text_analysis = pipeline.get_text_analysis(args.example_id)
    senses = pipeline.get_senses(args.example_id)
    
    if corrected is None:
        print(f"No corrected tokens for {args.example_id}")
        return
    
    if text_analysis is None:
        print(f"No analysis for {args.example_id}, run analyze first")
        return
    
    tokens = [t.corrected for t in corrected]
    
    predicates = []
    
    for i, sent_analysis in enumerate(text_analysis.sentences):
        print(f"\n--- Sentence {i+1} ---")
        
        try:
            pred = translate_analysis(sent_analysis, tokens, senses)
            predicates.append(pred)
            print(format_predicate(pred))
        except Exception as e:
            print(f"Error translating: {e}")
    
    # Store
    pipeline.store_predicates(args.example_id, predicates)
    print("\nStored predicates.")