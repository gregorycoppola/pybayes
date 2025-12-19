# src/qbbn/cli/commands/parse_implication.py
"""
Parse a sentence as an implication.
"""

import redis
from openai import OpenAI

from qbbn.core.pipeline import Pipeline
from qbbn.core.analyze_implication import analyze_implication
from qbbn.core.translate_implication import translate_implication
from qbbn.core.translate import format_predicate


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "parse-implication",
        help="Parse a sentence as an implication rule."
    )
    parser.add_argument("text", help="The implication sentence.")
    parser.add_argument("--db", type=int, default=0)
    parser.set_defaults(func=run)


def run(args):
    from qbbn.core.tokenize import tokenize, SpellCorrector
    
    redis_client = redis.Redis(host="localhost", port=6379, db=args.db)
    openai_client = OpenAI()
    
    # Quick tokenize + correct
    tokens = tokenize(args.text)
    token_texts = [t.text for t in tokens]
    
    corrector = SpellCorrector(openai_client)
    corrected = corrector.correct(tokens)
    corrected_texts = [c.corrected for c in corrected]
    
    print(f"Tokens: {corrected_texts}")
    
    # Check if it's an implication
    impl_struct = analyze_implication(corrected_texts, openai_client)
    
    if impl_struct is None:
        print("\nNot recognized as an implication.")
        return
    
    print(f"\nImplication detected:")
    print(f"  Antecedent: {corrected_texts[impl_struct.antecedent_start:impl_struct.antecedent_end]}")
    print(f"  Consequent: {corrected_texts[impl_struct.consequent_start:impl_struct.consequent_end]}")
    print(f"  Coreferences: {impl_struct.coreferences}")
    
    # Translate to logical form
    impl_link = translate_implication(corrected_texts, impl_struct, openai_client)
    
    print(f"\nLogical form:")
    vars_str = ", ".join(f"{v.name}:{v.type.name}" for v in impl_link.variables)
    print(f"  Ψ[{vars_str}]")
    print(f"  Premise:")
    print(format_predicate(impl_link.premise, indent=2))
    print(f"  → Conclusion:")
    print(format_predicate(impl_link.conclusion, indent=2))