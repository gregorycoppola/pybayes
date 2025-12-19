# src/qbbn/cli/commands/parse_nps.py
"""
Experimental: Find noun phrases in a clause.
"""

import json
from openai import OpenAI

from qbbn.core.tokenize import tokenize, SpellCorrector


SYSTEM_PROMPT = """You are a noun phrase detector.

Given numbered tokens from a clause, identify all noun phrases (NPs).

An NP is a noun with its modifiers (articles, adjectives, etc).

For "the big red dog chased a cat":
- NP 1: tokens 0-4 "the big red dog"
- NP 2: tokens 5-7 "a cat"

Reply with JSON:
{
  "nps": [
    {"start": 0, "end": 4, "head_index": 3},
    {"start": 5, "end": 7, "head_index": 6}
  ]
}

Rules:
- start is inclusive, end is exclusive
- head_index is the main noun
- Include determiners (the, a, an) and adjectives in the span
"""


def find_nps(tokens: list[str], client: OpenAI) -> dict:
    numbered = [f"{i}: {t}" for i, t in enumerate(tokens)]
    prompt = "Tokens:\n" + "\n".join(numbered)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    
    return json.loads(response.choices[0].message.content)


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "parse-nps",
        help="Find noun phrases in a sentence."
    )
    parser.add_argument("text", help="The sentence to parse.")
    parser.set_defaults(func=run)


def run(args):
    openai_client = OpenAI()
    
    # Quick tokenize + correct
    raw_tokens = tokenize(args.text)
    corrector = SpellCorrector(openai_client)
    corrected = corrector.correct(raw_tokens)
    tokens = [c.corrected for c in corrected]
    
    print(f"Tokens: {tokens}")
    print()
    
    result = find_nps(tokens, openai_client)
    
    print("Noun Phrases:")
    for np in result.get("nps", []):
        span = tokens[np["start"]:np["end"]]
        head = tokens[np["head_index"]] if "head_index" in np else "?"
        print(f"  [{np['start']}:{np['end']}] \"{' '.join(span)}\" (head: {head})")