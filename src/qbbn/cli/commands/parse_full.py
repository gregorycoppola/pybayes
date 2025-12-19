# src/qbbn/cli/commands/parse_full.py
"""
Experimental: Full parse - clauses then args.
"""

import json
from openai import OpenAI

from qbbn.core.tokenize import tokenize, SpellCorrector


CLAUSE_PROMPT = """Identify all clauses in this sentence.

CRITICAL: end index is EXCLUSIVE (Python slice style).
- If tokens are [0:the, 1:dog, 2:ran], and you want "the dog ran", use start=0, end=3 (NOT end=2)
- To include token 8, end must be 9

For "If someone is a man then they are mortal" (tokens 0-8):
- Clause 1: start=1, end=5 → "someone is a man" (verb_index=2)
- Clause 2: start=6, end=9 → "they are mortal" (verb_index=7)
- skip_tokens: [0, 5] → "If", "then"

Reply JSON:
{
  "clauses": [
    {"start": 1, "end": 5, "verb_index": 2, "label": "antecedent"},
    {"start": 6, "end": 9, "verb_index": 7, "label": "consequent"}
  ],
  "skip_tokens": [0, 5]
}
"""


ARG_PROMPT = """Identify arguments of the verb.

CRITICAL: end index is EXCLUSIVE (Python slice style).
- To include token at index 4, end must be 5
- tokens[start:end] should give the full argument

For clause "someone is a man" with verb "is" at index 1:
- agent: start=0, end=1 → "someone"
- theme: start=2, end=4 → "a man"

For clause "they are mortal" with verb "are" at index 1:
- agent: start=0, end=1 → "they"  
- theme: start=2, end=3 → "mortal"

Reply JSON:
{
  "arguments": [
    {"start": 0, "end": 1, "role": "agent"},
    {"start": 2, "end": 4, "role": "theme"}
  ]
}

Roles: agent, patient, theme, goal, source, location, instrument, time
"""


def find_clauses(tokens: list[str], client: OpenAI) -> dict:
    prompt = "Tokens:\n" + "\n".join(f"{i}: {t}" for i, t in enumerate(tokens))
    prompt += f"\n\nTotal: {len(tokens)} tokens (indices 0 to {len(tokens)-1})"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": CLAUSE_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def find_args_for_clause(tokens: list[str], verb_index: int, client: OpenAI) -> dict:
    prompt = "Clause tokens:\n" + "\n".join(f"{i}: {t}" for i, t in enumerate(tokens))
    prompt += f"\n\nVerb: {tokens[verb_index]} (index {verb_index})"
    prompt += f"\nTotal: {len(tokens)} tokens"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": ARG_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "parse-full",
        help="Full experimental parse: clauses → args."
    )
    parser.add_argument("text", help="The sentence to parse.")
    parser.set_defaults(func=run)


def run(args):
    openai_client = OpenAI()
    
    # Tokenize
    raw_tokens = tokenize(args.text)
    corrector = SpellCorrector(openai_client)
    corrected = corrector.correct(raw_tokens)
    tokens = [c.corrected for c in corrected]
    
    print(f"Tokens: {list(enumerate(tokens))}")
    print()
    
    # Step 1: Find clauses
    print("=== CLAUSES ===")
    clause_result = find_clauses(tokens, openai_client)
    
    clauses = clause_result.get("clauses", [])
    skip = clause_result.get("skip_tokens", [])
    
    for c in clauses:
        span = tokens[c["start"]:c["end"]]
        verb = tokens[c["verb_index"]] if c["verb_index"] < len(tokens) else "?"
        print(f"  [{c['start']}:{c['end']}] \"{' '.join(span)}\" verb={verb} ({c.get('label', '')})")
    
    if skip:
        print(f"  skip: {[(i, tokens[i]) for i in skip if i < len(tokens)]}")
    
    # Validate
    covered = set(skip)
    for c in clauses:
        covered.update(range(c["start"], c["end"]))
    missing = [i for i in range(len(tokens)) if i not in covered]
    if missing:
        print(f"  ⚠️  MISSING: {[(i, tokens[i]) for i in missing]}")
    else:
        print(f"  ✓ All tokens covered")
    
    # Step 2: For each clause (smallest first), find args
    print("\n=== ARGUMENTS ===")
    
    clauses_sorted = sorted(clauses, key=lambda c: c["end"] - c["start"])
    
    for c in clauses_sorted:
        clause_start = c["start"]
        clause_tokens = tokens[clause_start:c["end"]]
        verb_rel = c["verb_index"] - clause_start
        
        print(f"\nClause [{c['start']}:{c['end']}]: \"{' '.join(clause_tokens)}\"")
        print(f"  verb: {clause_tokens[verb_rel]} (relative index {verb_rel})")
        
        arg_result = find_args_for_clause(clause_tokens, verb_rel, openai_client)
        
        # Track coverage within clause
        covered_in_clause = {verb_rel}
        
        for a in arg_result.get("arguments", []):
            abs_start = a["start"] + clause_start
            abs_end = a["end"] + clause_start
            span = tokens[abs_start:abs_end]
            print(f"  {a['role']}: [{abs_start}:{abs_end}] \"{' '.join(span)}\"")
            covered_in_clause.update(range(a["start"], a["end"]))
        
        # Validate
        skip_words = {"a", "an", "the", ",", "."}
        clause_missing = [
            (i, clause_tokens[i]) 
            for i in range(len(clause_tokens)) 
            if i not in covered_in_clause and clause_tokens[i].lower() not in skip_words
        ]
        if clause_missing:
            print(f"  ⚠️  MISSING: {clause_missing}")
        else:
            print(f"  ✓ Clause complete")