# src/qbbn/cli/commands/parse_clauses.py
"""
Experimental: Find clauses in a sentence.
"""

import json
import redis
from openai import OpenAI

from qbbn.core.tokenize import tokenize, SpellCorrector


SYSTEM_PROMPT = """You are a clause boundary detector.

Given numbered tokens, identify ALL clauses (main and embedded).

A clause has a verb and its arguments. Sentences can contain multiple clauses.

For "If someone is a man then they are mortal":
- Clause 1: tokens 1-5 "someone is a man" (verb: is)
- Clause 2: tokens 6-9 "they are mortal" (verb: are)
- Skip tokens: 0 "If", 5 "then"

For "I think that you love her":
- Clause 1: tokens 0-6 "I think that you love her" (verb: think, outer)
- Clause 2: tokens 3-6 "you love her" (verb: love, embedded)

Reply with JSON:
{
  "clauses": [
    {"start": 1, "end": 5, "verb_index": 2, "label": "antecedent"},
    {"start": 6, "end": 9, "verb_index": 7, "label": "consequent"}
  ],
  "skip_tokens": [0, 5]
}

Rules:
- start is inclusive, end is exclusive
- verb_index is the main verb of that clause
- label is optional (antecedent/consequent/main/embedded/relative)
- skip_tokens are structural words (if, then, that, which, etc)
- embedded clauses can overlap with outer clauses
"""


def find_clauses(tokens: list[str], client: OpenAI) -> dict:
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
        "parse-clauses",
        help="Find clause boundaries in a sentence."
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
    
    result = find_clauses(tokens, openai_client)
    
    print("Clauses:")
    for c in result.get("clauses", []):
        span = tokens[c["start"]:c["end"]]
        verb = tokens[c["verb_index"]] if "verb_index" in c else "?"
        label = c.get("label", "")
        print(f"  [{c['start']}:{c['end']}] \"{' '.join(span)}\"")
        print(f"    verb: {verb} (index {c.get('verb_index')})")
        if label:
            print(f"    label: {label}")
    
    skip = result.get("skip_tokens", [])
    if skip:
        skip_words = [tokens[i] for i in skip]
        print(f"\nSkip tokens: {skip} = {skip_words}")
    
    # Validate coverage
    covered = set(skip)
    for c in result.get("clauses", []):
        covered.update(range(c["start"], c["end"]))
    
    missing = [i for i in range(len(tokens)) if i not in covered]
    if missing:
        print(f"\n⚠️  Missing tokens: {[(i, tokens[i]) for i in missing]}")
    else:
        print(f"\n✓ All tokens covered")