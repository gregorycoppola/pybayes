# src/qbbn/cli/commands/wsd.py
"""
Run word sense disambiguation on an example.
"""

import redis
from openai import OpenAI

from qbbn.core.pipeline import Pipeline
from qbbn.core.lexicon import Lexicon
from qbbn.core.state import get_namespace
from qbbn.core.wsd_select import select_sense
from qbbn.core.wsd_define import define_sense


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "wsd",
        help="Run word sense disambiguation (requires correct first)."
    )
    parser.add_argument("example_id", help="The example UUID.")
    parser.add_argument("--db", type=int, default=0)
    parser.set_defaults(func=run)


def run(args):
    client = redis.Redis(host="localhost", port=6379, db=args.db)
    namespace = get_namespace(client)
    pipeline = Pipeline(client)
    lexicon = Lexicon(client, prefix=f"{namespace}:lex")
    openai_client = OpenAI()
    
    corrected = pipeline.get_corrected(args.example_id)
    sentence = pipeline.get_raw(args.example_id)
    
    if corrected is None:
        print(f"No corrected tokens for {args.example_id}, run correct first")
        return
    
    symbols = []
    
    for token in corrected:
        word = token.corrected.lower()
        senses = lexicon.lookup_word(word)
        
        result = select_sense(word, sentence, senses, openai_client)
        
        if result == "add":
            definition = define_sense(word, sentence, openai_client)
            sense = lexicon.add(word, definition)
            print(f"{word} → {sense.symbol} (new: {definition})")
        else:
            sense = senses[result]
            print(f"{word} → {sense.symbol}")
        
        symbols.append(sense.symbol)
    
    pipeline.store_senses(args.example_id, symbols)
    print(f"\nStored: {symbols}")