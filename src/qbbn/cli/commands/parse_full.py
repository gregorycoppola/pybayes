# src/qbbn/cli/commands/parse_full.py
"""
Experimental: Full parse - clauses then NPs then roles.
"""

import json
from openai import OpenAI

from qbbn.core.tokenize import tokenize, SpellCorrector


def find_clauses(tokens: list[str], client: OpenAI) -> dict:
    prompt = "Tokens:\n" + "\n".join(f"{i}: {t}" for i, t in enumerate(tokens))
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """Identify all clauses. Reply JSON:
{"clauses": [{"start": 0, "end": 5, "verb_index": 2, "label": "main"}], "skip_tokens": []}
- start inclusive, end exclusive
- every token must be in a clause or skip_tokens"""},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def find_args_for_clause(tokens: list[str], verb_index: int, client: OpenAI) -> dict:
    prompt = f"Tokens:\n" + "\n".join(f"{i}: {t}" for i, t in enumerate(tokens))
    prompt += f"\n\nVerb: {tokens[verb_index]} (index {verb_index})"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """Identify arguments of the verb. Reply JSON:
{"arguments": [{"start": 0, "end": 2, "role": "agent"}, {"start": 3, "end": 5, "role": "theme"}]}
- Roles: agent, patient, theme, goal, source, location, instrument, time
- start inclusive, end exclusive
- Include all words in the argument span"""},
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
        print(f"  [{c['start']}:{c['end']}] \"{' '.join(span)}\" verb={tokens[c['verb_index']]} ({c.get('label', '')})")
    
    if skip:
        print(f"  skip: {[(i, tokens[i]) for i in skip]}")
    
    # Validate
    covered = set(skip)
    for c in clauses:
        covered.update(range(c["start"], c["end"]))
    missing = [i for i in range(len(tokens)) if i not in covered]
    if missing:
        print(f"  ⚠️  MISSING: {[(i, tokens[i]) for i in missing]}")
    
    # Step 2: For each clause, find args
    print("\n=== ARGUMENTS ===")
    
    # Sort by size (smallest first = most embedded first)
    clauses_sorted = sorted(clauses, key=lambda c: c["end"] - c["start"])
    
    for c in clauses_sorted:
        clause_tokens = tokens[c["start"]:c["end"]]
        # Adjust verb index to be relative to clause
        verb_rel = c["verb_index"] - c["start"]
        
        print(f"\nClause: \"{' '.join(clause_tokens)}\"")
        
        arg_result = find_args_for_clause(clause_tokens, verb_rel, openai_client)
        
        for a in arg_result.get("arguments", []):
            # Convert back to absolute indices for display
            abs_start = a["start"] + c["start"]
            abs_end = a["end"] + c["start"]
            span = tokens[abs_start:abs_end]
            print(f"  {a['role']}: [{abs_start}:{abs_end}] \"{' '.join(span)}\"")
        
        # Validate clause coverage
        arg_covered = {verb_rel}
        for a in arg_result.get("arguments", []):
            arg_covered.update(range(a["start"], a["end"]))
        
        clause_missing = [i for i in range(len(clause_tokens)) 
                         if i not in arg_covered 
                         and clause_tokens[i].lower() not in {"a", "an", "the", ",", "."}]
        if clause_missing:
            print(f"  ⚠️  MISSING in clause: {[(i, clause_tokens[i]) for i in clause_missing]}")