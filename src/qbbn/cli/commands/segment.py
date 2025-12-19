# src/qbbn/cli/commands/segment.py
"""
Segment text into sentences.
"""

import redis
from openai import OpenAI

from qbbn.core.pipeline import Pipeline
from qbbn.core.segment import segment_sentences


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "segment",
        help="Segment text into sentences (requires correct first)."
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
    
    sentences = segment_sentences(tokens, openai_client)
    
    print(f"Found {len(sentences)} sentence(s):")
    for i, (start, end) in enumerate(sentences):
        span = " ".join(tokens[start:end])
        print(f"  {i+1}. [{start}:{end}] {span}")
    
    pipeline.store_segments(args.example_id, sentences)
    print("\nStored segments.")